from models.legal_models import (
LegalDocument,
Division,
Provision
)
def normalise_document(doc: LegalDocument):
    chunks = []

    for division in doc.divisions:

        # -----------------------
        # DIVISION CHUNK
        # -----------------------
        chunks.append({
            "type": "division",
            "text": division.title,
            "meta": {
                "division_no": division.division_no,
                "document": doc.document_type
            }
        })

        for provision in division.provisions:

            # -----------------------
            # PROVISION CHUNK
            # -----------------------
            chunks.append({
                "type": "provision",
                "text": provision.text,
                "meta": {
                    "provision_no": provision.provision_no,
                    "title": provision.title,
                    "division_no": division.division_no
                }
            })

            for clause in provision.clauses:

                # -----------------------
                # CLAUSE CHUNK
                # -----------------------
                chunks.append({
                    "type": "clause",
                    "text": clause.text,
                    "meta": {
                        "clause_no": clause.clause_no,
                        "provision_no": provision.provision_no
                    }
                })

                for sub in clause.sub_clauses:

                    chunks.append({
                        "type": "subclause",
                        "text": sub.text,
                        "meta": {
                            "sub_clause_no": sub.sub_clause_no,
                            "clause_no": clause.clause_no
                        }
                    })

                    for roman in sub.roman_clauses:

                        chunks.append({
                            "type": "roman",
                            "text": roman.text,
                            "meta": {
                                "roman_no": roman.roman_no,
                                "sub_clause_no": sub.sub_clause_no
                            }
                        })

    return chunks
