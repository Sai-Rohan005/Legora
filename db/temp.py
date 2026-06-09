# # from Crypto.PublicKey import RSA
# # from Crypto.Hash import SHA256
# # from Crypto.Signature import pss


# # # ----------------------------
# # # 1. Generate RSA Key Pair
# # # ----------------------------
# # def generate_rsa_keys(bits=2048):
# #     key = RSA.generate(bits)

# #     private_key = key.export_key()
# #     public_key = key.publickey().export_key()

# #     return private_key, public_key


# # # ----------------------------
# # # 2. Save Keys to Files
# # # ----------------------------
# # def save_key(key_data, filename):
# #     with open(filename, "wb") as f:
# #         f.write(key_data)


# # # ----------------------------
# # # 3. Load Private Key
# # # ----------------------------
# # def load_private_key(filename="private.pem"):
# #     with open(filename, "rb") as f:
# #         return RSA.import_key(f.read())


# # # ----------------------------
# # # 4. Load Public Key
# # # ----------------------------
# # def load_public_key(filename="public.pem"):
# #     with open(filename, "rb") as f:
# #         return RSA.import_key(f.read())


# # # ----------------------------
# # # 5. Sign Message (RSA-PSS)
# # # ----------------------------
# # def sign_message(message, private_key):
# #     if isinstance(message, str):
# #         message = message.encode("utf-8")

# #     hash_obj = SHA256.new(message)
# #     signature = pss.new(private_key).sign(hash_obj)

# #     return signature


# # # ----------------------------
# # # 6. Verify Signature
# # # ----------------------------
# # def verify_signature(message, signature, public_key):
# #     if isinstance(message, str):
# #         message = message.encode("utf-8")

# #     hash_obj = SHA256.new(message)

# #     try:
# #         pss.new(public_key).verify(hash_obj, signature)
# #         return True
# #     except (ValueError, TypeError):
# #         return False


# # # ----------------------------
# # # 7. Example Usage
# # # ----------------------------
# # if __name__ == "__main__":

# #     # Generate keys
# #     private_key, public_key = generate_rsa_keys()

# #     # Save keys
# #     save_key(private_key, "private.pem")
# #     save_key(public_key, "public.pem")

# #     # Load keys
# #     priv = load_private_key("private.pem")
# #     pub = load_public_key("public.pem")

# #     # Message
# #     msg = "This is a legal RAG secure request"

# #     # Sign
# #     signature = sign_message(msg, priv)
# #     print("Signature generated:", signature.hex())

# #     # Verify
# #     is_valid = verify_signature(msg, signature, pub)
# #     print("Signature valid?", is_valid)


# import requests
# import os
# from dotenv import load_dotenv

# load_dotenv()

# API_TOKEN = os.getenv("kanoon_token")

# BASE_URL = "https://api.indiankanoon.org/search/"


# def search(query):
#     headers = {
#         "Authorization": f"Token {API_TOKEN}",
#         "Content-Type": "application/x-www-form-urlencoded"
#     }

#     data = {
#         "formInput": query
#     }

#     response = requests.post(BASE_URL, headers=headers, data=data)

#     print("STATUS:", response.status_code)
#     print("RESPONSE:", response.text)

#     try:
#         return response.json()
#     except:
#         return response.text


# print(search('"fundamental rights"'))




from neo4j import GraphDatabase

driver = GraphDatabase.driver(
    "bolt://localhost:7687",
    auth=("neo4j", "test12345")
)

with driver.session() as session:
    result = session.run("RETURN 1")
    print(result.single())

driver.close()