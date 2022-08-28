FROM python:3.10
WORKDIR /code
COPY requirements.txt /code/
RUN pip install -r requirements.txt
COPY main.py missions.py skill_lookup.py text_builders.py gacha_calc.py drops.py db.py quests.py /code/
CMD python main.py