baseUrl = "https://api.competitions.recall.network/api"
response = requests.get(
  f"{baseUrl}/account/portfolio",
  headers={
    "Content-Type": "application/json",
    "Authorization": `Bearer YOUR_API_KEY`,
  }
)
print(response.json())
#测试结果1
#测试结果2
#测试结果3
#测试结果4
#测试结果5
#测试结果6
#测试结果7
#测试结果8