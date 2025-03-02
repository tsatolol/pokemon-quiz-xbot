### build
docker build -t dev_lambda_func_image -f ./Dockerfile ./

### start
docker run -d --name dev_lambda_func_container -v "$(pwd)":/var/task -p 5000:5000 dev_lambda_func_image

### exec python app
docker exec dev_lambda_func_container python /var/task/app.py

### stop & remove
# docker stop dev_lambda_func_container
# docker rm dev_lambda_func_container
# docker rmi dev_lambda_func_image