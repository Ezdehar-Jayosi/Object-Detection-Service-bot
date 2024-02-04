pipeline {
    agent any

    environment {
        IMAGE_TAG = "v${env.BUILD_ID}-${env.BUILD_NUMBER}-${currentBuild.getTimeInMillis()}"
        AWS_REGION = "us-east-1"
        ECR_REPOSITORY = '933060838752.dkr.ecr.us-east-1.amazonaws.com'
        ACCOUNT_ID = '933060838752'
        KUBE_CONFIG_CRED = 'KUBE_CONFIG_CRED'
        CLUSTER_NAME = "k8s-main"
        CLUSTER_REGION = "us-east-1"
        NAMESPACE = "ezdeharj"
    }

    stages {

        stage('Authenticate with ECR') {
            steps {
                script {
                    // Authenticate Docker with ECR
                    sh "aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
                }
            }
        }

        stage('Build and Push Polybot') {
            steps {
                script {
                    // Build and push the Docker image for polybot
                    docker.build("${ECR_REPOSITORY}/ezdehar-polybot-img:${IMAGE_TAG}", ' .')
                    docker.image("${ECR_REPOSITORY}/ezdehar-polybot-img:${IMAGE_TAG}").push()
                }
            }
        }
        stage('Deploy to Kubernetes') {
            steps {
                script {
                    // Use the kubectl command from the configured kubeconfig
                    sh "kubectl --kubeconfig=${KUBE_CONFIG_CRED} config use-context ${CLUSTER_NAME}"

                    // Get the latest image tag from ECR
                    def latestImageTag = sh(script: "aws ecr describe-images --region ${CLUSTER_REGION} --repository-name ezdehar-polybot-img --query 'images[].imageTags' --output text | tr -s '\t' '\n' | sort -r | head -n 1", returnStdout: true).trim()

                    // Update the Kubernetes manifest with the latest image tag
                    sh "sed -i.bak 's|image: ${ECR_REPOSITORY}/ezdehar-polybot-img:latest|image: ${ECR_REPOSITORY}/ezdehar-polybot-img:${latestImageTag}|' polybot-deployment.yaml"

                    // Deploy to Kubernetes in the specified namespace
                    sh "kubectl --kubeconfig=${KUBE_CONFIG_CRED} apply -f polybot-deployment.yaml -n ${NAMESPACE}"

                    // Clean up backup file created by sed
                    sh "rm polybot-deployment.yaml.bak"
                }
            }
        }
    }
}
