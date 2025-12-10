#!/usr/bin/env python
#
# Cart Store implementations for Cart Service
# Supports Redis and in-memory storage

import os
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

import grpc
import redis

import demo_pb2

from logger import getJSONLogger

logger = getJSONLogger('cartservice-store')


class CartStore(ABC):
    """Abstract base class for cart storage implementations."""

    @abstractmethod
    def add_item(self, user_id: str, product_id: str, quantity: int) -> None:
        """Add an item to the user's cart."""
        pass

    @abstractmethod
    def get_cart(self, user_id: str) -> demo_pb2.Cart:
        """Get the user's cart."""
        pass

    @abstractmethod
    def empty_cart(self, user_id: str) -> None:
        """Empty the user's cart."""
        pass

    @abstractmethod
    def ping(self) -> bool:
        """Check if the store is healthy."""
        pass


class InMemoryCartStore(CartStore):
    """In-memory cart storage implementation."""

    def __init__(self):
        # Dictionary mapping user_id to a list of CartItems
        self._carts: Dict[str, Dict[str, int]] = {}
        logger.info("Using in-memory cart store")

    def add_item(self, user_id: str, product_id: str, quantity: int) -> None:
        logger.info(f"AddItem called: user_id={user_id}, product_id={product_id}, quantity={quantity}")

        if user_id not in self._carts:
            self._carts[user_id] = {}

        if product_id in self._carts[user_id]:
            self._carts[user_id][product_id] += quantity
        else:
            self._carts[user_id][product_id] = quantity

    def get_cart(self, user_id: str) -> demo_pb2.Cart:
        logger.info(f"GetCart called: user_id={user_id}")

        cart = demo_pb2.Cart(user_id=user_id)

        if user_id in self._carts:
            for product_id, quantity in self._carts[user_id].items():
                cart.items.append(demo_pb2.CartItem(
                    product_id=product_id,
                    quantity=quantity
                ))

        return cart

    def empty_cart(self, user_id: str) -> None:
        logger.info(f"EmptyCart called: user_id={user_id}")
        self._carts[user_id] = {}

    def ping(self) -> bool:
        return True


class RedisCartStore(CartStore):
    """Redis-based cart storage implementation."""

    def __init__(self, redis_addr: str):
        logger.info(f"Connecting to Redis at {redis_addr}")

        # Parse Redis address (format: host:port)
        if ':' in redis_addr:
            host, port = redis_addr.rsplit(':', 1)
            port = int(port)
        else:
            host = redis_addr
            port = 6379

        self._redis = redis.Redis(
            host=host,
            port=port,
            decode_responses=False  # We'll handle bytes manually for protobuf
        )

        # Test connection
        try:
            self._redis.ping()
            logger.info("Successfully connected to Redis")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def add_item(self, user_id: str, product_id: str, quantity: int) -> None:
        logger.info(f"AddItem called: user_id={user_id}, product_id={product_id}, quantity={quantity}")

        try:
            # Get existing cart or create new one
            cart_data = self._redis.get(user_id)

            if cart_data:
                cart = demo_pb2.Cart()
                cart.ParseFromString(cart_data)
            else:
                cart = demo_pb2.Cart(user_id=user_id)

            # Check if product already exists in cart
            existing_item = None
            for item in cart.items:
                if item.product_id == product_id:
                    existing_item = item
                    break

            if existing_item:
                existing_item.quantity += quantity
            else:
                cart.items.append(demo_pb2.CartItem(
                    product_id=product_id,
                    quantity=quantity
                ))

            # Save cart back to Redis
            self._redis.set(user_id, cart.SerializeToString())

        except redis.RedisError as e:
            logger.error(f"Redis error in add_item: {e}")
            raise grpc.RpcError(
                grpc.StatusCode.UNAVAILABLE,
                f"Can't access cart storage: {e}"
            )

    def get_cart(self, user_id: str) -> demo_pb2.Cart:
        logger.info(f"GetCart called: user_id={user_id}")

        try:
            cart_data = self._redis.get(user_id)

            if cart_data:
                cart = demo_pb2.Cart()
                cart.ParseFromString(cart_data)
                return cart

            # Return empty cart if user doesn't exist
            return demo_pb2.Cart(user_id=user_id)

        except redis.RedisError as e:
            logger.error(f"Redis error in get_cart: {e}")
            raise grpc.RpcError(
                grpc.StatusCode.UNAVAILABLE,
                f"Can't access cart storage: {e}"
            )

    def empty_cart(self, user_id: str) -> None:
        logger.info(f"EmptyCart called: user_id={user_id}")

        try:
            # Set an empty cart (instead of deleting, to match C# behavior)
            empty_cart = demo_pb2.Cart(user_id=user_id)
            self._redis.set(user_id, empty_cart.SerializeToString())

        except redis.RedisError as e:
            logger.error(f"Redis error in empty_cart: {e}")
            raise grpc.RpcError(
                grpc.StatusCode.UNAVAILABLE,
                f"Can't access cart storage: {e}"
            )

    def ping(self) -> bool:
        try:
            self._redis.ping()
            return True
        except redis.RedisError:
            return False


def create_cart_store() -> CartStore:
    """Factory function to create the appropriate cart store based on environment."""
    redis_addr = os.environ.get('REDIS_ADDR')
    alloydb_addr = os.environ.get('ALLOYDB_PRIMARY_IP')
    spanner_project = os.environ.get('SPANNER_PROJECT')
    spanner_connection = os.environ.get('SPANNER_CONNECTION_STRING')

    if redis_addr:
        logger.info(f"Using Redis cart store at {redis_addr}")
        return RedisCartStore(redis_addr)
    elif alloydb_addr:
        # AlloyDB support would require additional implementation
        logger.warning("AlloyDB support not yet implemented, falling back to in-memory")
        return InMemoryCartStore()
    elif spanner_project or spanner_connection:
        # Spanner support would require additional implementation
        logger.warning("Spanner support not yet implemented, falling back to in-memory")
        return InMemoryCartStore()
    else:
        logger.info("No external store configured, using in-memory cart store")
        return InMemoryCartStore()
