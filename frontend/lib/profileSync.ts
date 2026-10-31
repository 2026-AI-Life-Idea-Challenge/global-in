import { COUNTRY_CODES, VISA_CODES, PROFILE_KEY, readSaved, saveTab } from './consultation';

/** Merge only API-confirmed structured values; never infer a birth date or qualifications. */
export function syncConsultationProfile(profile: Record<string, unknown> | undefined) {
  if (!profile) return;
  const saved = readSaved<{ form?: Record<string, unknown>; profile?: Record<string, unknown> }>(PROFILE_KEY, {});
  const form = { ...saved.form };
  if (typeof profile.date_of_birth === 'string') form.age = profile.date_of_birth;
  if (Array.isArray(profile.nationalities)) form.nationality = profile.nationalities.join(', ');
  if (typeof profile.residence_country === 'string') form.residence = profile.residence_country;
  for (const [field, input] of Object.entries({ education: 'education', education_status: 'eduStatus', major: 'major', career: 'career', career_duration: 'careerDuration', languages: 'languages', certifications: 'certs' })) {
    if (typeof profile[field] === 'string' || (profile[field] === null && saved.profile?.[field] != null)) form[input] = profile[field] || '';
  }
  for (const [field, codes, selected, undecided] of [
    ['target_country', COUNTRY_CODES, 'selectedCountries', 'undecidedCountry'],
    ['target_visa_type', VISA_CODES, 'selectedPurposes', 'undecidedPurpose'],
  ] as const) {
    if (!(field in profile)) continue;
    if (profile[field] == null && saved.profile?.[field] == null) continue;
    const label = Object.entries(codes).find(([, code]) => code === profile[field])?.[0];
    form[selected] = label ? [label] : []; form[undecided] = !label;
  }
  saveTab(PROFILE_KEY, { ...saved, form, profile: { ...saved.profile, ...profile } });
}
