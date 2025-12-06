## Product Requirements

This document contains a list of requirements that every change made to this repository should meet.
Every change must:

1. Preserve the golden user journey taken by Kubernetes beginners.
1. Preserve the simplicity of demos.
1. Preserve the simplicity of the quickstart.

These requirements are about the default deployment (default configuration) of v-commerce.
Changes that will violate any of these rules should not be built into the default configuration of v-commerce.
Such changes should be opt-in only — ideally, as a [Kustomize Component](/kustomize) if they align with the [purpose of v-commerce](/docs/purpose.md).

### 1. Preserve the golden user journey taken by Kubernetes beginners

The following statement about v-commerce should always be true:

> A user can deploy v-commerce's default configuration on a [_kind_ Kubernetes cluster](https://kind.sigs.k8s.io/).

This statement describes the golden user journey that we expect new Kubernetes users to take while onboarding to v-commerce.

Being able to run v-commerce on a _kind_ cluster ensures that v-commerce is free and cloud-agnostic. v-commerce should be useful and accessible to developers that are new to Kubernetes.

### 2. Preserve the simplicity of demos

New changes should not complicate the primary user journey showcased in live demos and tutorials.

Today, the primary user journey is as follows:

1. Visit v-commerce on a web browser.
2. Select an item from the homepage and add the item to the cart.
3. The checkout form is pre-populated with placeholder data (e.g. the shipping address).
4. The user checks out and completes the order.

### 3. Preserve the simplicity of the quickstart

New changes should not add additional complexity in the main v-commerce quickstart.

In particular, new changes should not add extra required steps or additional required tools in that quickstart.

Ideally, extensions to v-commerce's default functionality (such as a new microservice or a new cloud service integration) should be added as a [Kustomize Component](/kustomize/components) which users can optionally opt into.
