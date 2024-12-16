# Example: reuse your existing OpenAI setup
from openai import OpenAI
import re
import json
# Point to the local server

# breakpoint()

system_prompt = """
Analyze the following expense text and output ONLY a JSON object with these fields:
Output: {
    "Amount": float,  # Amount in INR (numeric only, no currency symbols)
    "Source": string, # Account/card number
    "Destination": string, # Recipient
    "ExpenseType": string # Must be one of: ["House Rent/EMI","Utility Bills","Groceries and Household Items","Transportation","Healthcare","Education Expenses","Mobile and Internet Bills","Personal Care and Clothing","Entertainment and Recreation","Savings and Investments"]
}

Requirements:
1. Return ONLY the JSON object, no additional text
2. If expense type is unclear, exclude that message entirely
3. Amount should be numeric only (no "Rs" or other symbols)
4. Format numbers as floats (e.g., 480.0 not "480")
5. If the message is not an expense, return null for all fields
6. If the message is not clear, return null for all fields
7. Don't return any python code or other text
8. If the message is reminder for bill payment, return null for all fields
9. If the message is receipt of payment of credit card bill, return null for all fields
"""

user_prompt = """
Here is the text
"""
smses = ['Dear SBI User, your A/c X2684-debited by Rs480.0 on 19Dec22 transfer to tpslQR Ref No 235371592525. If not done by u, fwd this SMS to 9223008333/Call 1800111109 or 09449112211 to block UPI -SBI',
'Dear SBI User, your A/c X2684-debited by Rs274.0 on 16Dec22 transfer to AAPALA LAKI BAZAR Ref No 235017104112. If not done by u, fwd this SMS to 9223008333/Call 1800111109 or 09449112211 to block UPI -SBI',
'Hi, bill payment of Rs. 3004.0 paid via Upi towards your Airtel Xstream Fiber ID 0232410972795_dsl has been processed via Order Id 7007025809011666944. You will receive the payment posting confirmation within 1 Hrs. Please keep the Order ID for future reference',
'We are committed to make your experience beautiful with Airtel. For any assistance, please contact our team of expert advisors by dialing 198/121 from your Airtel number. In case if you are not satisfied with the resolution provided by the call centre, you can contact the Appellate authority on the same number.'
]


def analyze_sms(sms):
    user_prompt = sms
    client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")
    completion = client.chat.completions.create(
        model="lmstudio-community/Meta-Llama-3-8B-Instruct-GGUF",
        messages=[
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": user_prompt}
  ],
        temperature=0.8,
    )
    content = completion.choices[0].message.content
    # search for the json object
    json_obj = re.search(r'\{.*\}', content)
    del completion, client
    if json_obj:
        try:
            return content, json.loads(json_obj.group(0))
        except json.JSONDecodeError:
            try:
                return content, json.loads(content)
            except json.JSONDecodeError:
                return content, None
    else:
        return content, None
    

if __name__ == "__main__":
    for sms in smses:
        print('='*100)
        print('SMS:')
        print(sms)
        print('-'*100)
        content, json_obj = analyze_sms(sms)
        print('LLM Output:')
        print(content)
        print('-'*100)
        print('JSON Output:')
        print(json_obj)
        print('='*100)


