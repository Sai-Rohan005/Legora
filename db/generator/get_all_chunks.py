from models.legal_models import (
LegalDocument,
Division,
Provision
)
def normalise_document(doc: LegalDocument):
    chunks = []

    for division in doc.divisions:

        # DIVISION
        chunks.append({
            "type": "division",
            "text": division.title,
            "meta": {
                "division_no": division.division_no,
                "document": doc.document_type
            }
        })

        for provision in division.provisions:

            # PROVISION
            chunks.append({
                "type": "provision",
                "text": provision.text,
                "meta": {
                    "provision_no": provision.provision_no,
                    "title": provision.title,
                    "division_no": division.division_no,
                    "document": doc.document_type
                }
            })

            for clause in provision.clauses:

                # CLAUSE
                chunks.append({
                    "type": "clause",
                    "text": clause.text,
                    "meta": {
                        "clause_no": clause.clause_no,
                        "provision_no": provision.provision_no,
                        "document": doc.document_type
                    }
                })

                for sub in clause.sub_clauses:

                    # SUBCLAUSE
                    chunks.append({
                        "type": "subclause",
                        "text": sub.text,
                        "meta": {
                            "sub_clause_no": sub.sub_clause_no,
                            "clause_no": clause.clause_no,
                            "provision_no": provision.provision_no,
                            "document": doc.document_type
                        }
                    })

                    for roman in sub.roman_clauses:

                        # ROMAN
                        chunks.append({
                            "type": "roman",
                            "text": roman.text,
                            "meta": {
                                "roman_no": roman.roman_no,
                                "sub_clause_no": sub.sub_clause_no,
                                "clause_no": clause.clause_no,
                                "provision_no": provision.provision_no,
                                "document": doc.document_type
                            }
                        })

    return chunks