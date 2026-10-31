import Image from 'next/image';

const FLAG_CODES: Record<string, string> = {
  일본: 'jp', Japan: 'jp', japan: 'jp', JP: 'jp',
  독일: 'de', Germany: 'de', germany: 'de', DE: 'de',
  캐나다: 'ca', Canada: 'ca', canada: 'ca', CA: 'ca',
  호주: 'au', Australia: 'au', australia: 'au', AU: 'au',
  미국: 'us', USA: 'us', 'United States': 'us', usa: 'us', US: 'us',
};

export default function CountryFlag({ country, size = 22 }: { country?: string | null; size?: number }) {
  const code = country ? FLAG_CODES[country] : undefined;
  if (!code) {
    return <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="var(--mu)" strokeWidth="1.6" style={{ flexShrink: 0 }}>
      <circle cx="12" cy="12" r="10" />
      <path d="M2 12h20M12 2a15 15 0 0 1 0 20M12 2a15 15 0 0 0 0 20" />
    </svg>;
  }
  return <Image src={`/flags/${code}.${code === 'jp' ? 'svg' : 'png'}`} alt="" aria-hidden="true"
    width={size} height={size} unoptimized
    style={{ width: size, height: size, borderRadius: '50%', objectFit: 'contain', flexShrink: 0, display: 'inline-block', verticalAlign: 'middle', boxShadow: '0 0 0 1px rgba(0,0,0,0.06)' }} />;
}
