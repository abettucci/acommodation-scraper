# Dockerfile for building Lambda Layer
FROM public.ecr.aws/lambda/python:3.11

# Install build dependencies
RUN yum install -y gcc gcc-c++ make zip

# Copy requirements
COPY requirements.txt /tmp/requirements.txt

# Install Python dependencies to /opt/python (Lambda layer structure)
RUN pip install --no-cache-dir -r /tmp/requirements.txt -t /opt/python/

# Clean up unnecessary files to reduce layer size
RUN find /opt/python -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
RUN find /opt/python -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
RUN find /opt/python -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true

# Create the layer zip
WORKDIR /opt
RUN zip -r9 /tmp/layer.zip python/

# Default command copies the zip to output volume
CMD ["cp", "/tmp/layer.zip", "/output/layer.zip"]
