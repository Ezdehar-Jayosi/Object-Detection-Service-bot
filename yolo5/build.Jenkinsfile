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
                        if (!fileExtensionChanged('.yaml')) {
                            // Authenticate Docker with ECR using environment variables
                            sh "aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
                        } else {
                            echo 'Skipping build for excluded file extension.'
                        }
                    }
                }
            }
        }

        stage('Build and Push Yolo5') {
            steps {
                script {
                    if (!fileExtensionChanged('.yaml')) {
                        def dockerImage = docker.build("${ECR_REPOSITORY}/ezdehar-yolo5-img:${IMAGE_TAG}", './yolo5')
                        dockerImage.push()
                    } else {
                        echo 'Skipping build for excluded file extension.'
                    }
                }
            }
        }

        stage('Deploy Polybot') {
            steps {
                script {
                    try {
                        dir("${env.WORKSPACE}") {
                            withCredentials([usernamePassword(credentialsId: 'github', passwordVariable: 'GIT_PASSWORD', usernameVariable: 'GIT_USERNAME')]) {
                                if (!fileExtensionChanged('.yaml')) {
                                    sh "sed -i 's|image: .*|image: ${ECR_REPOSITORY}/ezdehar-yolo5-img:${IMAGE_TAG}|' k8s/yolo5-deployment.yaml"
                                    sh 'git config user.email "ezdeharj.95@gmail.com"'
                                    sh 'git config user.name "Ezdehar-Jayosi"'
                                    sh 'git add k8s/yolo5-deployment.yaml'
                                    sh 'git diff --cached --exit-code || git commit -m "Update image tag " && git push https://$GIT_USERNAME:$GIT_PASSWORD@github.com/Ezdehar-Jayosi/Object-Detection-Service-bot.git HEAD:main'
                                } else {
                                    echo 'Skipping build for excluded file extension.'
                                }
                            }
                        }
                    } catch (Exception e) {
                        currentBuild.result = 'FAILURE'
                        error("Failed to deploy yolo5: ${e.message}")
                    }
                }
            }
        }
    }

    // Function to check if a file with a certain extension has changed in the last commit
    def fileExtensionChanged(fileExtension) {
        def changedFiles = sh(script: "git diff --name-only HEAD^ HEAD", returnStdout: true).trim()
        return changedFiles.split('\n').any { it.endsWith(fileExtension) }
    }
}