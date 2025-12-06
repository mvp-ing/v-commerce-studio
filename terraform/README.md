# Use Terraform to deploy v-commerce

This page walks you through the steps required to deploy the v-commerce sample application on a Kubernetes cluster using Terraform.

**Note:** The Terraform configuration in this directory may need to be modified to match your specific infrastructure and cloud provider requirements.

## Prerequisites

1. A Kubernetes cluster or the ability to create one via Terraform
2. Terraform installed on your local machine
3. Appropriate cloud provider credentials configured (if using a cloud provider)

## Deploy the sample application

1. Clone the repository.

   ```bash
   git clone <your-repo-url>
   ```

1. Move into the `terraform/` directory which contains the Terraform installation scripts.

   ```bash
   cd v-commerce/terraform
   ```

1. Review and modify the `terraform.tfvars` file to match your configuration requirements.

1. Initialize Terraform.

   ```bash
   terraform init
   ```

1. See what resources will be created.

   ```bash
   terraform plan
   ```

1. Create the resources and deploy the sample.

   ```bash
   terraform apply
   ```

   1. If there is a confirmation prompt, type `yes` and hit Enter/Return.

   Note: This step can take about 10 minutes. Do not interrupt the process.

Once the Terraform script has finished, you can locate the frontend's external IP address to access the sample application.

```bash
kubectl get service frontend-external | awk '{print $4}'
```

## Clean up

To remove the individual resources created by Terraform:

1. Navigate to the `terraform/` directory.

1. Run the following command:

   ```bash
   terraform destroy
   ```

   1. If there is a confirmation prompt, type `yes` and hit Enter/Return.
