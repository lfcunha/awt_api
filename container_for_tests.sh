#!/usr/bin/env bash

ansible-vault decrypt /var/lib/jenkins/workspace/swt-test/swt/config-test.ini.vault --vault-password-file ~/.vault_pass.txt
mv /var/lib/jenkins/workspace/swt-test/swt/config-test.ini.vault /var/lib/jenkins/workspace/swt-test/swt/config.ini


# database container
docker rm -f dpcc_swt  || true
docker rm -f dbstore  || true
docker rm -f swt-test  || true
docker rmi -f lfcunha/swt-py-api:latest || true
#docker rmi -f swt-image || true

docker create --name dbstore  lfcunha/swt_test_data:latest  # data volume container
docker run --name dpcc_swt --volumes-from dbstore -v /dbdata:/var/lib/mysql -e MYSQL_ROOT_PASSWORD=passwd -d mysql:latest
# --user$(id -u)
#run test container
#docker build -t swt-image .
# run as non-root user, otherwise, jenkins can't delete files that belong to root (.tox files set up by running docker container)
docker run --rm --link dpcc_swt:db --name swt-test -d -v /var/lib/jenkins/workspace/swt-test:/opt/swt/SWT-FSE/ -w /opt/swt/SWT-FSE/ swt-image
#docker volume prune
#docker run --rm --name swt-chown -d -v /var/lib/jenkins/workspace/swt-test:/opt/swt/SWT-FSE/ -w /opt/swt/SWT-FSE/ swt-image sh -c 'exec chown -R jenkins:jenkins *'
#docker rmi


# https://github.com/rancher/convoy#quick-start-guide
# convoy mounts volumes with backends such as EBS

# docker commit --change='CMD ["apachectl", "-DFOREGROUND"]' -c "EXPOSE 80" c3f279d17e0a  svendowideit/testimage:version4

# https://go.cloudbees.com/docs/cloudbees-documentation/cje-user-guide/index.html#docker-workflow-sect-inside

# testing container
# https://www.levvel.io/blog-post/building-devops-artifact-pipeline-for-docker-containers/