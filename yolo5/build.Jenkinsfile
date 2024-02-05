pipeline {
    agent any

    environment {
        IMAGE_TAG = "v${env.BUILD_ID}-${env.BUILD_NUMBER}-${currentBuild.getTimeInMillis()}"
        AWS_REGION = "us-east-1"
        ECR_REPOSITORY = '933060838752.dkr.ecr.us-east-1.amazonaws.com'
        ACCOUNT_ID = '933060838752'
        KUBE_CONFIG_CRED = 'KUBE_CONFIG_CRED'
        CLUSTER_NAME = "k8s-main"  // Corrected cluster name
        CLUSTER_REGION = "us-east-1"
        NAMESPACE = "ezdeharj"
    }

    stages {
        stage('Authenticate with ECR') {
            steps {
                script {
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
                file(credentialsId: 'KUBE_CONFIG_CRED', variable: 'KUBECONFIG')
            ]) {
                // Print the content of the kubeconfig file for debugging
                sh "cat ${KUBECONFIG}"

                // Confirm the existence and content of the kubeconfig file
                sh "ls -l ${KUBECONFIG}"

                // Use the kubectl command from the configured kubeconfig
                sh "kubectl --kubeconfig=${KUBECONFIG} config use-context k8s-main"
                sh "kubectl --kubeconfig=${KUBECONFIG} config view"

                // Rest of your deployment steps
            }
        }
    }
}

    }
}
