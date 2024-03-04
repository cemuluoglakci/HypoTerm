# 🥶 HypoTermQA

Hypothetical Terms Dataset for Benchmarking Hallucination Tendency of LLMs

## 📚 Table of contents

- 📘 [Introduction](#-introduction)
- 📜 [Publication](#-publication)
- 📝 [Citation](#-citation)
- 🚀 [Usage and Examples](#-usage-and-examples)
- 📋 [Requirements](#-requirements)
- 🔧 [Set Up](#-set-up)
- 👋 [Contact](#-contact)
- 🙏 [Acknowledgements](#-acknowledgements)


## 📘 Introduction

HypoTermQA repository contains 

* 📊 The HypoTermQA Benchmarking Dataset <a href="https://github.com/cemuluoglakci/HypoTermQA/tree/main/HypoTermQA_Dataset" class="button">View Dataset</a> 
* 💻 The sample code to use the HypoTermQA Dataset on LLMs <a href="https://github.com/cemuluoglakci/HypoTermQA/tree/main/sample_prompting" class="button">View Code</a>
* 🧪 The sample code to evaluate hallucination tendency of LLMs <a href="https://github.com/cemuluoglakci/HypoTermQA/tree/main/sample_evaluation" class="button">View Code</a>
* 📜 The sample code to reproduce the paper <a href="https://github.com/cemuluoglakci/HypoTermQA/tree/main/sample_reproduction" class="button">View Code</a>
* 🔄 Intermediate results of the dataset generation process <a href="https://github.com/cemuluoglakci/HypoTermQA/tree/main/data/intermediate" class="button">View Results</a>
* 📈 Intermediate results of the LLM evaluation process <a href="https://github.com/cemuluoglakci/HypoTermQA/tree/main/data/evaluation" class="button">View Results</a>

## 📜 Publication

This repository contains the implementation of our research presented in the following paper:

[HypoTermQA: Hypothetical Terms Dataset for Benchmarking Hallucination Tendency of LLMs](https://arxiv.org/abs/2402.16211)

The paper was presented at EACL SRW 2024. You can see the poster we presented below:

![Poster Image](./images/poster.png)

## 📝 Citation

Our paper will be published in the proceedings of EACL SRW 2024. The citation details will be updated once the proceedings are published. Please check back for updates.

In the meantime, you can cite our work as follows:

```bibtex
@misc{uluoglakci2024hypotermqa,
  title={HypoTermQA: Hypothetical Terms Dataset for Benchmarking Hallucination Tendency of LLMs},
  author={Cem Uluoglakci and Tugba Taskaya Temizel},
  year={2024},
  howpublished={To appear in the proceedings of EACL SRW 2024}
}
```

## 🚀 Usage and Examples

This repository contains several examples that demonstrate different aspects of the HypoTermQA Dataset and its usage with LLMs:

* 💻 [Using the HypoTermQA Dataset with LLMs](https://github.com/cemuluoglakci/HypoTermQA/tree/main/sample_prompting): These examples show how to use the HypoTermQA Dataset with Language Models.
* 🧪 [Evaluating Hallucination Tendency of LLMs](https://github.com/cemuluoglakci/HypoTermQA/tree/main/sample_evaluation): These examples demonstrate how to evaluate the hallucination tendency of Language Models using our dataset.
* 📜 [Reproducing the Paper](https://github.com/cemuluoglakci/HypoTermQA/tree/main/sample_reproduction): These examples provide the code necessary to reproduce hypothetical dataset creation process.


## 📋 Requirements

1. PYTHON_VERSION=3.10.5
2. Ollama Container
3. MySql Server
4. Mongo DB
5. Milvus DB
6. Pytorch (https://pytorch.org/get-started/locally/)

## 🔧 Set Up

Follow these steps to set up the development environment:

1. Create a virtual environment:

    For Unix or MacOS, run:
    ```bash
    python3 -m venv venv
    ```

    For Windows, run:
    ```powershell
    python -m venv venv
    ```

2. Activate the virtual environment:

    On Unix or MacOS, run:
    ```bash
    source venv/bin/activate
    ```

    On Windows, run:
    ```powershell
    .\venv\Scripts\activate
    ```

3. Install the required packages:

    ```bash
    pip install -r requirements.txt
    ```


## 👋 Contact

If you have any questions, issues, or if you need support with the project, you can get in touch with us:

* GitHub: [GitHub Profile](https://github.com/cemuluoglakci)


Please feel free to report any bugs or issues, we appreciate your feedback!

## 🙏 Acknowledgements

The computational experiments conducted with open LLMs in this study were fully performed at TUBITAK ULAKBIM, High Performance and Grid Computing Center (TRUBA resources).