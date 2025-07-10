baseUrl = "https://api.competitions.recall.network/api"
response = requests.get(
  f"{baseUrl}/account/portfolio",
  headers={
    "Content-Type": "application/json",
    "Authorization": `Bearer YOUR_API_KEY`,
  }
)
print(response.json())
#测试结果
