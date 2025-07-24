crawl:
	@echo "Running crawl script with config file: ${config_file}"
	export PYTHONPATH=$(shell pwd) && \
	python scripts/run_crawl.py --config_file=${config_file}

preprocess:
	@echo "Running preprocess script with config file: ${config_file}"
	export PYTHONPATH=$(shell pwd) && \
	python scripts/run_preprocess.py --config_file=${config_file}