run: extract transform train predict

extract:
	python src/extract.py

transform:
	python src/transform.py

train:
	python src/train.py

predict:
	python src/predict.py
