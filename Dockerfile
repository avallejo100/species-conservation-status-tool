FROM python:3.12

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY conservation_status.py /code/conservation_status.py

RUN chmod ugo+x /code/conservation_status.py

ENV PATH="/code:$PATH"