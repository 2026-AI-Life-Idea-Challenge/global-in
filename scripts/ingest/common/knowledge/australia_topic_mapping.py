"""Explicit source-heading mapping; original snapshot topics remain untouched."""
TOPICS={}
for prefix,names in {
    'AU_191_REGIONAL_PROVISIONAL': ['qualifying_visa','income_evidence','health','character','australian_values_statement','government_debt_and_immigration_history'],
    'AU_491':['invitation','state_nomination_or_family_sponsorship','age','skills_assessment','points','english','eligible_occupation','health','character','government_debt','australian_values_statement'],
    'AU_494_EMPLOYER_SPONSORED':['age','employer_nomination','relevant_skills_and_qualifications','skills_assessment','english','health','character','government_debt','australian_values_statement'],
    'AU_494_LABOUR_AGREEMENT':['labour_agreement_occupation','age','relevant_skills_and_qualifications','skills_assessment','english','health','character','government_debt','australian_values_statement'],
}.items():
    for index,topic in enumerate(names,1):TOPICS[f'{prefix}_POL_{index:02d}']=topic
