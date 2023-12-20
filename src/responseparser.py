import json
import re

class LLmResponseParser:
    def __init__(self):
        pass

    def _loop_double_quotes(self, json_str):
        i = 0
        while i<50:
            i += 1
            try:
                response = json.loads(json_str)
                return json_str
            except Exception as e:
                if e.msg == "Expecting ',' delimiter":
                    if json_str[e.pos-1] == '"':
                        json_str = json_str[:e.pos-1] + re.sub('"', "'", json_str[e.pos-1:], 2)
    
                    else:
                        json_str = json_str[:e.pos] + "," + json_str[e.pos:]
                else:
                    return json_str
    
    def parse_response(self, json_str):
        initial_string = json_str.replace('WARNING: Failed to parse response: ','')
        response_string = initial_string.replace('<|im_end|>','').strip()
    
        try:
            return json.loads(response_string)
        except:
            pass
        
        try:
            response_string = response_string[response_string.find("{"):response_string.find("}")+1].strip()
            return json.loads(response_string)
        except:
            pass
        
        try:
            response_string = response_string.lower()
            return json.loads(response_string, strict=False)
        except:
            pass
        
        try:
            response_string =  response_string.replace('"\n"', '",\n"')
            return json.loads(response_string, strict=False)
        except Exception as e:
            pass
        
        try:
            response_string = self._loop_double_quotes(response_string)
            return json.loads(response_string, strict=False)
        except Exception as e:
            raise e