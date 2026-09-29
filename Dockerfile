# Imagem base oficial do AWS Lambda para Python 3.12
FROM public.ecr.aws/lambda/python:3.12

# Diretório padrão da tarefa Lambda: /var/task
WORKDIR ${LAMBDA_TASK_ROOT}

# Copia os arquivos de dependências
COPY requirements.txt .

# Instala as dependências no ambiente do Lambda
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código da aplicação
COPY app/ ./app/

# Define o entrypoint do handler (arquivo app/main.py -> variável handler)
CMD [ "app.main.handler" ]
