from db.neo4j_store import Neo4jStore


def print_node(data):

    if not data:
        print("Node not found")
        return

    print("\n" + "=" * 80)
    print("NODE")
    print("=" * 80)

    for k, v in data["node"].items():
        print(f"{k}: {v}")

    print("\n" + "=" * 80)
    print("NEIGHBORS")
    print("=" * 80)

    for neighbor in data["neighbors"]:

        relation = neighbor.get(
            "relation"
        )

        node = neighbor.get(
            "neighbor"
        )

        print(f"\n[{relation}]")

        if node:

            for k, v in node.items():

                if k == "text":

                    print(
                        f"{k}: "
                        f"{str(v)[:300]}"
                    )

                else:

                    print(
                        f"{k}: {v}"
                    )


def main():

    graph = Neo4jStore(
        uri="bolt://localhost:7687",
        username="neo4j",
        password="test12345"
    )

    while True:

        node_id = input(
            "\nEnter node id "
            "(or quit): "
        )

        if node_id.lower() == "quit":
            break

        result = (
            graph.get_node_with_neighbors(
                node_id
            )
        )

        print_node(
            result
        )

    graph.close()


if __name__ == "__main__":
    main()