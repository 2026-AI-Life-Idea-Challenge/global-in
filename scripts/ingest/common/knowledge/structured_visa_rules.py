"""Explicit age conditions from the reviewed registry; dates are event-specific."""
def rules():
    maxima={'BE':30,'CA':35,'CY':35,'DK':35,'EE':30,'FI':35,'FR':35,'DE':35,'HK':30,'IE':35,'IT':35,'JP':30,'MT':30,'NL':30,'NO':30,'KR':35,'SE':30,'TW':30,'GB':35}
    def age(event,minimum=0,maximum=None):
        return dict(operator='age_range',birth_field='date_of_birth',event_field=event,minimum=minimum,maximum=maximum)
    result={}
    for suffix in ('FIRST_POL_02','SECOND_POL_05','THIRD_POL_05'):
        result['AU_417_'+suffix]={**age('application_date',18), 'passport_maximum':maxima,'event_not_before':'2026-07-01'}
        result['AU_462_'+suffix]={**age('application_date',18,30),'event_not_before':'2026-07-01'}
    for pid in ('AU_189_PT_POL_04','AU_190_POL_05'):
        result[pid]=age('invitation_date',maximum=44)
    result['AU_407_POL_03']=dict(operator='any',children=[age('application_date',18),dict(operator='manual_check',reason='미성년자에게 발급하는 것이 합리적인지 장관 재량 확인')])
    for pid in ('AU_186_DE_POL_06','AU_186_LA_POL_04','AU_186_TRT_POL_06'):
        result[pid]=dict(operator='any',children=[age('application_date',maximum=44),dict(operator='manual_check',reason='해당 스트림의 법정 연령 면제·협약 양허·기간별 경과규정 심사')])
    return result
