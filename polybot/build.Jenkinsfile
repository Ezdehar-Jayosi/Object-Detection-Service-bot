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
                        // Authenticate Docker with ECR using environment variables
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
            try {
                dir("${env.WORKSPACE}") {
                    withCredentials([usernamePassword(credentialsId: 'github', passwordVariable: 'GIT_PASSWORD', usernameVariable: 'GIT_USERNAME')]) {
                        sh "sed -i 's|image: .*|image: ${ECR_REPOSITORY}/ezdehar-polybot-img:${IMAGE_TAG}|' k8s/polybot-deployment.yaml"
                        sh 'git config user.email "ezdeharj.95@gmail.com"'
                        sh 'git config user.name "Ezdehar-Jayosi"'
                        sh 'git add k8s/polybot-deployment.yaml'
                        sh 'git commit -m "Update image tag "'
                        sh 'git push https://$GIT_USERNAME:$GIT_PASSWORD@github.com/Ezdehar-Jayosi/Object-Detection-Service-bot/k8s.git HEAD:main '
                    }
                }
            } catch (Exception e) {
                currentBuild.result = 'FAILURE'
                error("Failed to deploy Polybot: ${e.message}")
            }
        }
    }
}

    }
}
