FROM public.ecr.aws/lambda/python
COPY ./ ${LAMBDA_TASK_ROOT}
RUN pip install --no-cache-dir -r requirements.txt
CMD [ "app.lambda_handler" ]
