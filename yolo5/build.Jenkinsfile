pipeline {
    agent any

    environment {
        IMAGE_TAG = "v${env.BUILD_ID}-${env.BUILD_NUMBER}-${currentBuild.getTimeInMillis()}"
        AWS_REGION = "us-east-1"
        ECR_REPOSITORY = '933060838752.dkr.ecr.us-east-1.amazonaws.com'
        ACCOUNT_ID = '933060838752'
        CLUSTER_NAME = "k8s-main"
        CLUSTER_REGION = "us-east-1"
    }

    stages {

        stage('Authenticate with ECR') {
            steps {
                script {
                    def AWS_CREDENTIALS = [
                        [$class: 'StringBinding', credentialsId: 'AWS_ACCESS_KEY_ID', variable: 'AWS_ACCESS_KEY_ID'],
                        [$class: 'StringBinding', credentialsId: 'AWS_SECRET_ACCESS_KEY', variable: 'AWS_SECRET_ACCESS_KEY']
                    ]

                    // Use withCredentials to securely pass AWS credentials
                    withCredentials(AWS_CREDENTIALS) {
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
                    if (dockerImage) {
                        dockerImage.push()
                    } else {
                        error "Docker image build failed."
                    }
                }
            }
        }

        stage('Deploy to Kubernetes') {
            steps {
                script {
                    def AWS_CREDENTIALS = [
                        [$class: 'StringBinding', credentialsId: 'AWS_ACCESS_KEY_ID', variable: 'AWS_ACCESS_KEY_ID'],
                        [$class: 'StringBinding', credentialsId: 'AWS_SECRET_ACCESS_KEY', variable: 'AWS_SECRET_ACCESS_KEY'],
                        [$class: 'FileBinding', credentialsId: 'KUBE_CONFIG_CRED', variable: 'KUBECONFIG']
                    ]

                    // Use the kubectl command from the configured kubeconfig
                    withCredentials(AWS_CREDENTIALS) {
                        sh "kubectl --kubeconfig=${KUBECONFIG} config use-context ${CLUSTER_NAME}"

                        // Get the latest image tag from ECR for yolo5
                        def latestImageTagYolo5 = sh(script: "aws ecr describe-images --region ${CLUSTER_REGION} --repository-name ezdehar-yolo5-img --query 'images[].imageTags' --output text | tr -s '\t' '\n' | sort -r | head -n 1", returnStdout: true).trim()

                        // Update the Kubernetes manifest with the latest image tag for yolo5
                        sh "sed -i.bak 's|image: ${ECR_REPOSITORY}/ezdehar-yolo5-img:latest|image: ${ECR_REPOSITORY}/ezdehar-yolo5-img:${latestImageTagYolo5}|' yolo5-deployment.yaml"

                        // Deploy to Kubernetes in the specified namespace
                        sh "kubectl --kubeconfig=${KUBECONFIG} apply -f yolo5-deployment.yaml -n ${latestImageTagYolo5}"

                        // Clean up backup file created by sed
                        sh "rm yolo5-deployment.yaml.bak"
                    }
                }
            }
        }
    }
}
