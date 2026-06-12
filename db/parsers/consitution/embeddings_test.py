
from __future__ import annotations

import json
import pickle
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer


# =========================================================
# EMBEDDING GENERATOR
# =========================================================

class EmbeddingGenerator:

    def __init__(
        self,
        model_name: str = "BAAI/bge-large-en-v1.5"
    ):

        self.model = SentenceTransformer(
            model_name
        )

    # =====================================================
    # GENERATE
    # =====================================================

    def generate(
        self,
        chunks: list,
        batch_size: int = 32
    ):

        texts = [
            chunk.text
            for chunk in chunks
        ]

        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True
        )

        return embeddings

    # =====================================================
    # SAVE NUMPY
    # =====================================================

    def save_embeddings(
        self,
        embeddings,
        output_path: str
    ):

        np.save(
            output_path,
            embeddings
        )

    # =====================================================
    # SAVE COMPLETE DATASET
    # =====================================================

    def save_dataset(
        self,
        chunks,
        embeddings,
        output_file: str
    ):

        records = []

        for chunk, embedding in zip(
            chunks,
            embeddings
        ):

            records.append(
                {
                    "chunk_id":
                        chunk.chunk_id,

                    "chunk_type":
                        chunk.chunk_type,

                    "text":
                        chunk.text,

                    "metadata":
                        chunk.metadata,

                    "references":
                        chunk.references,

                    "embedding":
                        embedding.tolist()
                }
            )

        with open(
            output_file,
            "w",
            encoding="utf8"
        ) as f:

            json.dump(
                records,
                f,
                ensure_ascii=False
            )

    # =====================================================
    # PICKLE
    # =====================================================

    def save_pickle(
        self,
        chunks,
        embeddings,
        output_file
    ):

        data = []

        for chunk, embedding in zip(
            chunks,
            embeddings
        ):

            data.append(
                {
                    "chunk_id":
                        chunk.chunk_id,

                    "chunk_type":
                        chunk.chunk_type,

                    "text":
                        chunk.text,

                    "metadata":
                        chunk.metadata,

                    "references":
                        chunk.references,

                    "embedding":
                        embedding
                }
            )

        with open(
            output_file,
            "wb"
        ) as f:

            pickle.dump(
                data,
                f
            )


# =========================================================
# EXAMPLE
# =========================================================

if __name__ == "__main__":

    from constitution_parser import ConstitutionParser
    from chunker_test import LegalChunker

    with open(
        "../../pdfs/constitution.txt",
        "r",
        encoding="utf8"
    ) as f:

        text = f.read()

    # -----------------------------------------
    # Parse
    # -----------------------------------------

    parser = ConstitutionParser()

    constitution = parser.parse(
        text
    )

    # -----------------------------------------
    # Chunk
    # -----------------------------------------

    chunker = LegalChunker()

    chunks = chunker.chunk_constitution(
        constitution
    )

    print(
        "Chunks:",
        len(chunks)
    )

    # -----------------------------------------
    # Embeddings
    # -----------------------------------------

    generator = EmbeddingGenerator()

    embeddings = generator.generate(
        chunks
    )

    print(
        "Embeddings Shape:",
        embeddings.shape
    )

    # -----------------------------------------
    # Save
    # -----------------------------------------

    generator.save_embeddings(
        embeddings,
        "constitution_embeddings.npy"
    )

    generator.save_pickle(
        chunks,
        embeddings,
        "constitution_dataset.pkl"
    )

    print(
        "Saved successfully"
    )

