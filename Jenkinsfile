def tests_passed = false;
node {
    stage('env'){
        //sh 'printenv'
        sh 'echo def vars'
        sh 'echo test_only: ${test_only}'
        sh 'echo branch: ${branch}'
        def test_only = env.test_only
        def branch = env.branch
    }

    stage('clean up old images and containers'){
        sh 'docker rm -f dpcc_swt_db  || true'
        sh 'docker rm -f dbstore  || true'
        sh 'docker rm -f swt-test  || true'
        sh 'docker rmi -f lfcunha/swt-api:latest || true'
        sh 'docker rmi -f swt-image || true'
        sh 'docker volume prune || true'

        // clean up old untagged images
        sh 'docker rmi $(docker images | grep "^<none>" | awk "{print $3}") || true'
    }

    stage('checkout repo') {
          if (env.branch == "develop" ) {
                //git branch: 'develop', url: 'git@github.com:sbour/swt-api.git', credentialsId: "github-ssh"
                git branch: 'develop', url: 'https://github.com/sbour/swt-api.git', credentialsId: "github-https"
          }
          if (env.branch == "staging" ) {
                git branch: 'staging', url: 'https://github.com/sbour/swt-api.git', credentialsId: "github-https"
          }
          if (env.branch == "master" ) {
                git branch: 'master', url: 'https://github.com/sbour/swt-api.git', credentialsId: "github-https"
          }
          dir('flask-restful') {
            git branch: 'master', url: 'https://github.com/lfcunha/flask-restful_LC.git', credentialsId: "github-https"
          }
      sh "git rev-parse HEAD > .git/commit-id"
   }

    stage('create test config') {
        sh 'ansible-vault decrypt /var/lib/jenkins/workspace/swt-api/swt/config-test.ini.vault --vault-password-file ~/.vault_pass.txt'
        sh 'mv /var/lib/jenkins/workspace/swt-api/swt/config-test.ini.vault /var/lib/jenkins/workspace/swt-api/swt/config.ini'
    }

   stage('create data container'){
        sh 'docker create --name dbstore 485656689961.dkr.ecr.us-east-1.amazonaws.com/swt-api-test_sql_data:update'
        sh 'docker run --name dpcc_swt_db --volumes-from dbstore -e MYSQL_ROOT_PASSWORD=passwd -d mysql:latest'
    }

   stage('create image for tests'){
        sh 'docker build -t swt-image .'
   }

   stage('create container for tests'){
        sh 'docker run --rm --link dpcc_swt_db:db --name swt-test -d -v /var/lib/jenkins/workspace/swt-api:/opt/swt/swt-api/ -w /opt/swt/swt-api/ swt-image'
   }

   stage('read the tests') {
       //sh 'rm /var/lib/jenkins/workspace/swt-test/res.xml'
       //step([$class: 'JUnitResultArchiver', testResults: '/var/lib/jenkins/workspace/swt-test/res.xml'])
       //def res = fileExists("/var/lcib/jenkins/workspace/swt-test/res.xml")
        waitUntil {
                fileExists 'res.xml'
        }
        try {
            //step([$class: 'JUnitResultArchiver', testResults: '**/target/surefire-reports/TEST-*.xml'])
            def output = sh 'python3 scripts/parse_junit_xml.py'   //readFile('result').trim()
            echo "output=$output";
            echo "YAY - tests passed";
            tests_passed = true;
            //currentBuild.result = 'SUCCESS';
        } catch (Exception _) {
            echo "OOPS - Tests failed";
            currentBuild.result = 'FAILURE';
        }
   }

    stage('prepare build') {
        if (tests_passed) {
            stage('change container command') {
                       if (env.test_only == "false" ) {
                                sh " sed -i -- 's/^CMD/#-CMD/g' Dockerfile"
                                sh " sed -i -- 's/^#CMD/CMD/g' Dockerfile"
                            }
             }
             stage('prepare config') {
                  sh 'rm -f /var/lib/jenkins/workspace/swt-test/swt/config.ini'

                  if (env.branch == "develop" ) {
                        sh 'ansible-vault decrypt /var/lib/jenkins/workspace/swt-api/swt/config-dev.ini.vault --vault-password-file ~/.vault_pass.txt'
                        sh 'mv /var/lib/jenkins/workspace/swt-api/swt/config-dev.ini.vault /var/lib/jenkins/workspace/swt-api/swt/config.ini'
                  }
                  if (env.branch == "staging" ) {
                        sh 'ansible-vault decrypt /var/lib/jenkins/workspace/swt-api/swt/config-stag.ini.vault --vault-password-file ~/.vault_pass.txt'
                        sh 'mv /var/lib/jenkins/workspace/swt-api/swt/config-stag.ini.vault /var/lib/jenkins/workspace/swt-api/swt/config.ini'
                  }
                  if (env.branch == "master" ) {
                        sh 'ansible-vault decrypt /var/lib/jenkins/workspace/swt-api/swt/config-prod.ini.vault --vault-password-file ~/.vault_pass.txt'
                        sh 'mv /var/lib/jenkins/workspace/swt-api/swt/config-prod.ini.vault /var/lib/jenkins/workspace/swt-api/swt/config.ini'
                  }
              }

              stage('Push image ') {
                    def commit_id = readFile('.git/commit-id').trim()
                    sh "echo commit_id: ${commit_id}"

                    //stage('... to dockerhub'){
                    //   docker.withRegistry("https://registry.hub.docker.com", "docker-hub") {
                    //       app = docker.build "lfcunha/swt-api" //this builds the remote image
                    //       app.push('latest')
                    //       app.push("${commit_id}")
                    //       currentBuild.result = 'SUCCESS'
                    //    }
                    //}

                     stage('Push image to ecr'){
                        app = docker.build "lfcunha/swt-api"
                        sh 'echo commit in push to ecr: ${commit_id}'
                        //sh "\$(aws ecr get-login --no-include-email --region us-east-1)"
                        sh "\$(aws ecr get-login --region us-east-1)"

                        if (env.branch == "develop" ) {
                            sh 'docker tag lfcunha/swt-api:latest 485656689961.dkr.ecr.us-east-1.amazonaws.com/swt-api_dev:latest'
                            sh 'docker push 485656689961.dkr.ecr.us-east-1.amazonaws.com/swt-api_dev:latest'

                            sh "docker tag lfcunha/swt-api:latest 485656689961.dkr.ecr.us-east-1.amazonaws.com/swt-api_dev:${commit_id}"
                            sh "docker push 485656689961.dkr.ecr.us-east-1.amazonaws.com/swt-api_dev:${commit_id}"
                        }
                        if (env.branch == "staging" ) {
                            sh 'docker tag lfcunha/swt-api:latest 485656689961.dkr.ecr.us-east-1.amazonaws.com/swt-api_stag:latest'
                            sh 'docker push 485656689961.dkr.ecr.us-east-1.amazonaws.com/swt-api_stag:latest'

                            sh "docker tag lfcunha/swt-api:latest 485656689961.dkr.ecr.us-east-1.amazonaws.com/swt-api_stag:${commit_id}"
                            sh "docker push 485656689961.dkr.ecr.us-east-1.amazonaws.com/swt-api_stag:${commit_id}"
                        }
                        if (env.branch == "master" ) {
                            sh 'docker tag lfcunha/swt-api:latest 485656689961.dkr.ecr.us-east-1.amazonaws.com/swt-api_prod:latest'
                            sh 'docker push 485656689961.dkr.ecr.us-east-1.amazonaws.com/swt-api_prod:latest'

                            sh "docker tag lfcunha/swt-api:latest 485656689961.dkr.ecr.us-east-1.amazonaws.com/swt-api_prod:${commit_id}"
                            sh "docker push 485656689961.dkr.ecr.us-east-1.amazonaws.com/swt-api_prod:${commit_id}"
                        }
                    }
                    stage('update ecs'){
                        if (env.branch == "develop" ) {
                            sh 'aws ecs update-service --region us-east-1  --cluster swt-api-DEV --service swt-api-pdev-service --desired-count 0'
                            sh 'aws ecs register-task-definition --region us-east-1  --cli-input-json file:///home/ubuntu/task_Def.json'
                            sh 'aws ecs update-service --region us-east-1  --cluster swt-api-DEV --service swt-api-dev-service --task-definition  swt-api_dev_task'
                            sh 'aws ecs update-service --region us-east-1  --cluster swt-api-DEV --service swt-api-dev-service --desired-count 1'
                        }
                        if (env.branch == "staging" ) {
                            sh 'aws ecs update-service --region us-east-1 --cluster swt-api-STAG --service swt-api-prod-service --desired-count 0'
                            sh 'aws ecs register-task-definition --region us-east-1 --cli-input-json file:///home/ubuntu/task_Def.json'
                            sh 'aws ecs update-service --region us-east-1 --cluster swt-api-STAG --service swt-api-stag-service --task-definition  swt-api_stag_task'
                            sh 'aws ecs update-service --region us-east-1 --cluster swt-api-STAG --service swt-api-stag-service --desired-count 1'
                        }
                        if (env.branch == "master" ) {
                            sh 'aws ecs update-service --region us-east-1 --cluster swt-api-PROD --service swt-api-prod-service --desired-count 0'
                            sh 'aws ecs register-task-definition --region us-east-1  --cli-input-json file:///home/ubuntu/task_Def.json'
                            sh 'aws ecs update-service --region us-east-1  --cluster swt-api-PROD --service swt-api-prod-service --task-definition  swt-api_prod_task'
                            sh 'aws ecs update-service --region us-east-1  --cluster swt-api-PROD --service swt-api-prod-service --desired-count 1'
                        }
                    }
             }
      }
    }

    stage("clean dir"){
            def commit_id = readFile('.git/commit-id').trim()
            sh "echo clean commit_id: ${commit_id}"
            sh "docker rmi -f lfcunha/swt-api:latest || true"
            sh "docker rmi -f 485656689961.dkr.ecr.us-east-1.amazonaws.com/swt-api_dev:latest || true"
            sh "docker rmi -f 485656689961.dkr.ecr.us-east-1.amazonaws.com/swt-api_dev || true"
            sh "docker rmi -f 485656689961.dkr.ecr.us-east-1.amazonaws.com/swt-api_dev:${commit_id} || true"
            sh "docker rmi -f 485656689961.dkr.ecr.us-east-1.amazonaws.com/swt-api_stag:latest || true"
            sh "docker rmi -f 485656689961.dkr.ecr.us-east-1.amazonaws.com/swt-api_stag || true"
            sh "docker rmi -f 485656689961.dkr.ecr.us-east-1.amazonaws.com/swt-api_stag:${commit_id} || true"
            sh "docker rmi -f 485656689961.dkr.ecr.us-east-1.amazonaws.com/swt-api_prod:latest || true"
            sh "docker rmi -f 485656689961.dkr.ecr.us-east-1.amazonaws.com/swt-api_prod || true"
            sh "docker rmi -f 485656689961.dkr.ecr.us-east-1.amazonaws.com/swt-api_prod:${commit_id} || true"

            sh 'docker rm -f dpcc_swt_db  || true'
            sh 'docker rm -f dbstore  || true'
            sh 'docker rmi -f lfcunha/swt-api:latest || true'
            sh 'docker rmi -f swt-image || true'
            sh 'docker rmi $(docker images -f dangling=true -q) || true'

            sh 'docker stop $(docker ps -a -q) || true'
            sh 'docker rm $(docker ps -a -q) || true'

            sh 'docker volume prune || true'
            sh 'docker volume rm $(docker volume ls -f dangling=true -q) || true'

            sh 'sudo chown -R jenkins:jenkins /var/lib/jenkins/workspace/swt-api/*'
            sh 'sudo chown -R jenkins:jenkins /var/lib/jenkins/workspace/swt-api/.[^.]*'
            deleteDir()
            currentBuild.result = 'SUCCESS'
    }
}
