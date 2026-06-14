from __future__ import annotations

from db.embedder import (
    LegalEmbedder
)

from db.vector_store import (
    QdrantStore
)

from symspellpy import SymSpell, Verbosity

sym_spell = SymSpell(
    max_dictionary_edit_distance=2,
    prefix_length=7
)

sym_spell.load_dictionary(
    "frequency_dictionary_en_82_765.txt",
    term_index=0,
    count_index=1
)


def spell_correct(text: str) -> str:

    suggestions = sym_spell.lookup_compound(
        text,
        max_edit_distance=2
    )

    if suggestions:
        return suggestions[0].term

    return text

class LegalSearcher:

    def __init__(
        self,
        collection_name: str =
        "legal_rag"
    ):

        self.embedder = (
            LegalEmbedder()
        )

        self.store = (
            QdrantStore(
                collection_name=
                    collection_name
            )
        )

    # =====================================================
    # SEARCH
    # =====================================================

    def search(
        self,
        query: str,
        limit: int = 10
    ):

        query_vector = (
            self.embedder
            .embed_query(
                query
            )
        )

        results = (
            self.store.search(
                query_vector,
                limit=limit
            )
        )

        return results

    # =====================================================
    # PRETTY PRINT
    # =====================================================

    def print_results(
        self,
        results
    ):

        for rank, point in enumerate(
            results.points,
            start=1
        ):

            payload = (
                point.payload
            )

            print(
                "\n" +
                "=" * 80
            )

            print(
                f"Rank      : {rank}"
            )

            print(
                f"Score     : "
                f"{point.score:.4f}"
            )

            print(
                f"Chunk ID  : "
                f"{payload.get('chunk_id')}"
            )

            print(
                f"Document  : "
                f"{payload.get('document')}"
            )

            print(
                f"Level     : "
                f"{payload.get('level')}"
            )

            if payload.get(
                "chapter_no"
            ):
                print(
                    f"Chapter   : "
                    f"{payload['chapter_no']}"
                )

            if payload.get(
                "section_no"
            ):
                print(
                    f"Section   : "
                    f"{payload['section_no']}"
                )

            if payload.get(
                "article_no"
            ):
                print(
                    f"Article   : "
                    f"{payload['article_no']}"
                )

            print()

            print(
                payload.get(
                    "text",
                    ""
                )[:2000]
            )


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    searcher = (
        LegalSearcher(
            collection_name=
                "legal_rag"
        )
    )
    hard_queries = [
    "attemptive mudder",
        "can police arrest me without magistrate permission",
        "facts accepted by court without proof",
        "government cannot take away my freedom without following law",
        "computer records admissible in court",
        "person killed while protecting property from robbery",
        "proof responsibility of accused",
        "maximum time police can keep arrested person before court",
        "freedom of speech restrictions",
        "when witness statement can be used after witness dies",
        "person dies after making statement explaining cause of death"
    ]
    expert_queries = [
        "attemptive mudder",
        "judical notice",
        "burdan of proof",
        "wife can testify against husband in criminal case",
        "secondary evidence of lost document",
        "statement made before death about cause of death",
        "when police officer can arrest without warrant",
        "person resisting lawful apprehension",
        "right of private defence causing death",
        "electronic record certificate requirements",
        "facts court must presume unless disproved",
        "who has burden of proving exception in criminal case",
        "anticipatory bail before arrest",
        "public document versus private document",
        "admission made by agent binding principal",
        "constitutional remedy against state action",
        "freedom of speech reasonable restrictions",
        "offence committed outside india by indian citizen",
        "confession made to police officer admissibility",
        "expert opinion relevance in court"
    ]



    output_file = "retrieval_results.txt"

    with open(output_file, "w", encoding="utf-8") as f:

        for query in hard_queries:
            query = spell_correct(query)

            if not query:
                continue

            results = searcher.search(
                query=query,
                limit=10
            )

            f.write("=" * 100 + "\n")
            f.write(f"QUERY: {query}\n")
            f.write("=" * 100 + "\n\n")

            for rank, result in enumerate(results, start=1):
                f.write(f"Rank {rank}\n")
                f.write(str(result))
                f.write("\n\n")

    print(f"Results saved to {output_file}")





    # for query in hard_queries:

    #     if not query:

    #         continue

    #     if query.lower() in {
    #         "exit",
    #         "quit"
    #     }:
    #         break

    #     results = (
    #         searcher.search(
    #             query=query,
    #             limit=10
    #         )
    #     )

    #     searcher.print_results(
    #         results
    #     )