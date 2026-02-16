FROM python:3.11-slim

WORKDIR /workspace
COPY requirements-governance.txt /workspace/requirements-governance.txt
RUN pip install --no-cache-dir -r /workspace/requirements-governance.txt
COPY . /workspace

ENV PYTHONPATH=/workspace
