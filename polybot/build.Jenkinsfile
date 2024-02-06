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
                    withCredentials([
                        string(credentialsId: 'AWS_ACCESS_KEY_ID', variable: 'AWS_ACCESS_KEY_ID'),
                        string(credentialsId: 'AWS_SECRET_ACCESS_KEY', variable: 'AWS_SECRET_ACCESS_KEY')
                    ]) {
                        //   Authenticate Docker with ECR using environment variables
                        sh "aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
                    }
                }
            }
        }

        stage('Build and Push Polybot') {
            steps {
                script {
                    def dockerImage = docker.build("${ECR_REPOSITORY}/ezdehar-polybot-img:${IMAGE_TAG}", './polybot')
                    dockerImage.push()
                }
            }
        }

       stage('Deploy Polybot') {
            steps {
                script {

                    HOME = "${env.WORKSPACE}"
                    withCredentials([
                        string(credentialsId: 'AWS_ACCESS_KEY_ID', variable: 'AWS_ACCESS_KEY_ID'),
                        string(credentialsId: 'AWS_SECRET_ACCESS_KEY', variable: 'AWS_SECRET_ACCESS_KEY'),
                    ]) {
                        sh 'aws eks update-kubeconfig --region ${CLUSTER_REGION} --name ${CLUSTER_NAME}'
                        sh "sed -i 's|image: .*|image: ${ECR_REPOSITORY}/ezdehar-polybot-img:${IMAGE_TAG}|' k8s/polybot-deployment.yaml"
                        sh 'kubectl apply -f k8s/polybot-deployment.yaml'
                    }
                }
            }
        }
    }

}