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
                    // Use withCredentials to securely pass AWS credentials
                    withCredentials([
                        string(credentialsId: 'AWS_ACCESS_KEY_ID', variable: 'AWS_ACCESS_KEY_ID'),
                        string(credentialsId: 'AWS_SECRET_ACCESS_KEY', variable: 'AWS_SECRET_ACCESS_KEY')
                    ]) {
                        // Authenticate Docker with ECR using environment variables
                        sh "aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
                    }
                }
            }
        }

        stage('Build and Push Yolo5') {
            steps {
                script {
                    def dockerImage = docker.build("${ECR_REPOSITORY}/ezdehar-yolo5-img:${IMAGE_TAG}", './yolo5')
                    dockerImage.push()
                }
            }
        }

        stage('Deploy to Kubernetes') {
            steps {
                script {
                    withCredentials([
                        string(credentialsId: 'AWS_ACCESS_KEY_ID', variable: 'AWS_ACCESS_KEY_ID'),
                        string(credentialsId: 'AWS_SECRET_ACCESS_KEY', variable: 'AWS_SECRET_ACCESS_KEY'),
                        file(credentialsId: 'KUBE_CONFIG_CRED', variable: 'KUBE_CONFIG_CRED')
                    ]) {
                        // Use the kubectl command from the configured kubeconfig
                        sh "kubectl --kubeconfig=${KUBE_CONFIG_CRED} config use-context ${CLUSTER_NAME}"

                        // Get the latest image tag from ECR for yolo5
                        def latestImageTagYolo5 = sh(script: "aws ecr describe-images --region ${CLUSTER_REGION} --repository-name ezdehar-yolo5-img --query 'images[].imageTags' --output text | tr -s '\t' '\n' | sort -r | head -n 1", returnStdout: true).trim()

                        // Update the Kubernetes manifest with the latest image tag for yolo5
                        sh "sed -i.bak 's|image: ${ECR_REPOSITORY}/ezdehar-yolo5-img:latest|image: ${ECR_REPOSITORY}/ezdehar-yolo5-img:${latestImageTagYolo5}|' yolo5-deployment.yaml"

                        // Deploy to Kubernetes in the specified namespace
                        sh "kubectl --kubeconfig=${KUBE_CONFIG_CRED} apply -f yolo5-deployment.yaml -n ${NAMESPACE}"

                        // Clean up backup file created by sed
                        sh "rm yolo5-deployment.yaml.bak"
                    }
                }
            }
        }
    }
}
