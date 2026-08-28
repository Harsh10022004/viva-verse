import requests
import json

url = 'https://leetcode.com/graphql'
query = '''
query categoryTopicList($categories: [String!]!, $first: Int!, $skip: Int!) {
  categoryTopicList(categories: $categories, first: $first, skip: $skip) {
    edges {
      node {
        id
        title
        post {
          content
        }
      }
    }
  }
}
'''
variables = {
    'categories': ['interview-experience'],
    'first': 5,
    'skip': 0
}

try:
    res = requests.post(url, json={'query': query, 'variables': variables}, headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})
    print(json.dumps(res.json(), indent=2))
except Exception as e:
    print('Error:', e)
