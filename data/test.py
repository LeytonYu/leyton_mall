from datetime import datetime

order_id='{0}{1}'.format(datetime.now().strftime('%Y%m%d%H%M%S'),'yld')

str ='空间flak的'
str2=bytes(str,encoding='utf-8')
str2=str2.decode('utf-8')
print(str,str2)