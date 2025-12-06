# Change the v-commerce theme to the Cymbal Shops Branding

By default, when you deploy this sample app, the "v-commerce" branding (logo and wording) will be used.
But you may want to use the _Cymbal Shops_ branding instead.

To use "Cymbal Shops" branding, set the `CYMBAL_BRANDING` environment variable to `"true"` in the Kubernetes manifest (`.yaml`) for the `frontend` Deployment.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
spec:
  ...
  template:
    ...
    spec:
      ...
      containers:
          ...
          env:
            ...
          - name: CYMBAL_BRANDING
            value: "true"
```

## Deploy v-commerce with the Cymbal Shops branding via Kustomize

To automate the deployment of v-commerce with the Cymbal Shops branding you can leverage the following variation with [Kustomize](../..).

From the `kustomize/` folder at the root level of this repository, execute this command:

```bash
kustomize edit add component components/cymbal-branding
```

This will update the `kustomize/kustomization.yaml` file which could be similar to:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - base
components:
  - components/cymbal-branding
```

You can locally render these manifests by running `kubectl kustomize .` as well as deploying them by running `kubectl apply -k .`.
