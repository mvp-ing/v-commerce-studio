#!/usr/bin/python
#
 

import os
import time
import logging

from google.cloud import secretmanager_v1
from urllib.parse import unquote
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from flask import Flask, request

from langchain_google_alloydb_pg import AlloyDBEngine, AlloyDBVectorStore

# ============================================
# Datadog APM and LLM Observability Setup
# ============================================
from ddtrace import tracer, patch_all
from ddtrace.llmobs import LLMObs

# Configure Datadog tracer with service name
tracer.configure(
    service=os.getenv("DD_SERVICE", "shopping-assistant-service"),
)

# Initialize Datadog tracing (auto-patches Flask, LangChain)
patch_all()

# Initialize LLM Observability (agentless mode)
LLMObs.enable(
    ml_app=os.getenv("DD_LLMOBS_ML_APP", "v-commerce-shopping-assistant"),
    agentless_enabled=os.getenv("DD_LLMOBS_AGENTLESS_ENABLED", "true").lower() == "true",
)

def emit_shopping_assistant_metrics(input_tokens: int, output_tokens: int, duration_ms: float,
                                     docs_retrieved: int = 0, model_name: str = "gemini-1.5-flash"):
    """Emit custom Shopping Assistant metrics to Datadog"""
    span = tracer.current_span()
    if span:
        span.set_tag("llm.model", model_name)
        span.set_tag("llm.tokens.input", input_tokens)
        span.set_tag("llm.tokens.output", output_tokens)
        span.set_tag("llm.tokens.total", input_tokens + output_tokens)
        span.set_tag("llm.request.duration_ms", duration_ms)
        span.set_tag("rag.docs_retrieved", docs_retrieved)
        
        # Estimate cost (Gemini 1.5 Flash pricing)
        input_cost = (input_tokens / 1_000_000) * 0.075
        output_cost = (output_tokens / 1_000_000) * 0.30
        span.set_tag("llm.tokens.total_cost_usd", input_cost + output_cost)

# Configure logging with Datadog trace correlation
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "severity": "%(levelname)s", "message": "%(message)s", "dd.trace_id": "%(dd.trace_id)s", "dd.span_id": "%(dd.span_id)s"}',
    datefmt='%Y-%m-%dT%H:%M:%S.%fZ'
)
logger = logging.getLogger(__name__)

# ============================================

PROJECT_ID = os.environ["PROJECT_ID"]
REGION = os.environ["REGION"]
ALLOYDB_DATABASE_NAME = os.environ["ALLOYDB_DATABASE_NAME"]
ALLOYDB_TABLE_NAME = os.environ["ALLOYDB_TABLE_NAME"]
ALLOYDB_CLUSTER_NAME = os.environ["ALLOYDB_CLUSTER_NAME"]
ALLOYDB_INSTANCE_NAME = os.environ["ALLOYDB_INSTANCE_NAME"]
ALLOYDB_SECRET_NAME = os.environ["ALLOYDB_SECRET_NAME"]

secret_manager_client = secretmanager_v1.SecretManagerServiceClient()
secret_name = secret_manager_client.secret_version_path(project=PROJECT_ID, secret=ALLOYDB_SECRET_NAME, secret_version="latest")
secret_request = secretmanager_v1.AccessSecretVersionRequest(name=secret_name)
secret_response = secret_manager_client.access_secret_version(request=secret_request)
PGPASSWORD = secret_response.payload.data.decode("UTF-8").strip()

engine = AlloyDBEngine.from_instance(
    project_id=PROJECT_ID,
    region=REGION,
    cluster=ALLOYDB_CLUSTER_NAME,
    instance=ALLOYDB_INSTANCE_NAME,
    database=ALLOYDB_DATABASE_NAME,
    user="postgres",
    password=PGPASSWORD
)

# Create a synchronous connection to our vectorstore
vectorstore = AlloyDBVectorStore.create_sync(
    engine=engine,
    table_name=ALLOYDB_TABLE_NAME,
    embedding_service=GoogleGenerativeAIEmbeddings(model="models/embedding-001"),
    id_column="id",
    content_column="description",
    embedding_column="product_embedding",
    metadata_columns=["id", "name", "categories"]
)

def create_app():
    app = Flask(__name__)

    @app.route("/", methods=['POST'])
    def talkToGemini():
        start_time = time.time()
        logger.info("Beginning RAG call")
        prompt = request.json['message']
        prompt = unquote(prompt)
        
        # Start LLM Observability workflow span for the entire RAG pipeline
        with LLMObs.workflow(
            name="shopping_assistant.rag_pipeline",
            ml_app="v-commerce-shopping-assistant"
        ) as workflow_span:
            LLMObs.annotate(
                span=workflow_span,
                input_data=prompt,
                metadata={"has_image": "image" in request.json}
            )

            # Step 1 – Get a room description from Gemini-vision-pro
            with LLMObs.llm(
                model_name="gemini-1.5-flash",
                model_provider="google",
                name="vision_description",
                ml_app="v-commerce-shopping-assistant"
            ) as vision_span:
                llm_vision = ChatGoogleGenerativeAI(model="gemini-1.5-flash")
                message = HumanMessage(
                    content=[
                        {
                            "type": "text",
                            "text": "You are a professional interior designer, give me a detailed decsription of the style of the room in this image",
                        },
                        {"type": "image_url", "image_url": request.json['image']},
                    ]
                )
                LLMObs.annotate(span=vision_span, input_data="[Image Analysis Request]")
                response = llm_vision.invoke([message])
                logger.info(f"Description step: {response}")
                description_response = response.content
                LLMObs.annotate(span=vision_span, output_data=description_response)

            # Step 2 – Similarity search with the description & user prompt
            with LLMObs.retrieval(
                name="vector_search",
                ml_app="v-commerce-shopping-assistant"
            ) as retrieval_span:
                vector_search_prompt = f""" This is the user's request: {prompt} Find the most relevant items for that prompt, while matching style of the room described here: {description_response} """
                logger.info(f"Vector search prompt: {vector_search_prompt}")

                docs = vectorstore.similarity_search(vector_search_prompt)
                logger.info(f"Retrieved documents: {len(docs)}")
                
                # Prepare relevant documents for inclusion in final prompt
                relevant_docs = ""
                doc_contexts = []
                for doc in docs:
                    doc_details = doc.to_json()
                    logger.info(f"Adding relevant document to prompt context: {doc_details}")
                    relevant_docs += str(doc_details) + ", "
                    doc_contexts.append(str(doc_details))
                
                LLMObs.annotate(
                    span=retrieval_span,
                    input_data=vector_search_prompt,
                    output_data=doc_contexts,
                    metadata={"docs_count": len(docs)}
                )

            # Step 3 – Tie it all together by augmenting our call to Gemini-pro
            with LLMObs.llm(
                model_name="gemini-1.5-flash",
                model_provider="google",
                name="design_recommendation",
                ml_app="v-commerce-shopping-assistant"
            ) as design_span:
                llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")
                design_prompt = (
                    f" You are an interior designer that works for Online Boutique. You are tasked with providing recommendations to a customer on what they should add to a given room from our catalog. This is the description of the room: \n"
                    f"{description_response} Here are a list of products that are relevant to it: {relevant_docs} Specifically, this is what the customer has asked for, see if you can accommodate it: {prompt} Start by repeating a brief description of the room's design to the customer, then provide your recommendations. Do your best to pick the most relevant item out of the list of products provided, but if none of them seem relevant, then say that instead of inventing a new product. At the end of the response, add a list of the IDs of the relevant products in the following format for the top 3 results: [<first product ID>], [<second product ID>], [<third product ID>] ")
                logger.info(f"Final design prompt: {design_prompt}")
                
                LLMObs.annotate(span=design_span, input_data=design_prompt)
                design_response = llm.invoke(design_prompt)
                LLMObs.annotate(span=design_span, output_data=design_response.content)

            # Emit metrics
            duration_ms = (time.time() - start_time) * 1000
            input_tokens = (len(prompt) + len(description_response) + len(relevant_docs)) // 4
            output_tokens = len(design_response.content) // 4
            emit_shopping_assistant_metrics(input_tokens, output_tokens, duration_ms, len(docs))
            
            # Annotate workflow output
            LLMObs.annotate(
                span=workflow_span,
                output_data=design_response.content,
                metadata={
                    "docs_retrieved": len(docs),
                    "duration_ms": duration_ms
                }
            )

            data = {'content': design_response.content}
            return data

    return app

if __name__ == "__main__":
    # Create an instance of flask server when called directly
    app = create_app()
    app.run(host='0.0.0.0', port=8080)
