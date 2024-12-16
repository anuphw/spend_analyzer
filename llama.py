import json
import re
from typing import Tuple, Optional, Dict, Any
import ollama

system_prompt = """
Analyze the following expense text and output ONLY a JSON object with these fields:
Output: {
    "Amount": float,  # Amount in INR (numeric only, no currency symbols)
    "Type": string, # Must be one of: ["Debit", "Credit"]
    "Source": string, # Account/card number
    "Destination": string, # Recipient
    "Category": string # Must be one of: ["House Rent/EMI","Utility Bills","Groceries and Household Items","Transportation","Healthcare","Education Expenses","Mobile and Internet Bills","Personal Care and Clothing","Entertainment and Recreation","Savings and Investments"]
}

Requirements:
1. Return ONLY the JSON object, no additional text
2. If expense type is unclear, exclude that message entirely
3. Amount should be numeric only (no "Rs" or other symbols)
4. Format numbers as floats (e.g., 480.0 not "480")
5. If the message is not an expense, return "Not expense" (not expense)
6. If the amount is not clear, return  "Amount not clear" (not expense)
7. Don't return any python code or other text
8. If the message is reminder for bill payment, return "Bill payment reminder" (not expense)
9. If the message is receipt of payment of credit card bill, return "Credit card bill payment receipt" (not expense)
10. If money is requested, then return "Money requested" (not expense)
11. If the money is credited/refunded, then return "Money credited/refunded" (not expense)
"""

def analyze_sms(sms: str) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    Analyze SMS text using Ollama to extract expense information.
    
    Args:
        sms: The SMS text to analyze
        
    Returns:
        Tuple containing (raw_llm_output, parsed_json_object)
    """
    try:
        # Generate response using Ollama
        response = ollama.generate(
            model='llama3.3:latest',
            prompt=f"{system_prompt}\n\nHere is the text to analyze:\n{sms}",
        )
        
        # Extract content from response
        content = response['response']
        
        # Search for JSON object in the response
        json_obj = re.search(r'\{.*\}', content)
        
        if json_obj:
            try:
                return content, json.loads(json_obj.group(0))
            except json.JSONDecodeError:
                try:
                    return content, json.loads(content)
                except json.JSONDecodeError:
                    return content, None
        else:
            try:
                return content, json.loads(content)
            except Exception as e:
                print(f"Error during generation: {str(e)}")
                return content, {}
            
    except Exception as e:
        print(f"Error during generation: {str(e)}")
        return "", None

# Sample SMS messages
smses = [
    'Dear SBI User, your A/c X2684-debited by Rs480.0 on 19Dec22 transfer to tpslQR Ref No 235371592525. If not done by u, fwd this SMS to 9223008333/Call 1800111109 or 09449112211 to block UPI -SBI',
    'Dear SBI User, your A/c X2684-debited by Rs274.0 on 16Dec22 transfer to AAPALA LAKI BAZAR Ref No 235017104112. If not done by u, fwd this SMS to 9223008333/Call 1800111109 or 09449112211 to block UPI -SBI',
    'Hi, bill payment of Rs. 3004.0 paid via Upi towards your Airtel Xstream Fiber ID 0232410972795_dsl has been processed via Order Id 7007025809011666944. You will receive the payment posting confirmation within 1 Hrs. Please keep the Order ID for future reference',
    'We are committed to make your experience beautiful with Airtel. For any assistance, please contact our team of expert advisors by dialing 198/121 from your Airtel number. In case if you are not satisfied with the resolution provided by the call centre, you can contact the Appellate authority on the same number.'
]

if __name__ == "__main__":
    for sms in smses:
        print('=' * 100)
        print('SMS:')
        print(sms)
        print('-' * 100)
        print('LLM Output:')
        content, json_obj = analyze_sms(sms)
        print(content)
        print('-' * 100)
        print('JSON Output:')
        print(json_obj)
        print('=' * 100)