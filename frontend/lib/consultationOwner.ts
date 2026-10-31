import 'server-only';
import { createHmac, randomBytes } from 'node:crypto';
import { cookies } from 'next/headers';
import { NextRequest } from 'next/server';

/** Browser ownership is separate from an authenticated account identity. */
export class CrossOriginConsultation extends Error {}
export async function consultationOwner(req: NextRequest, apiKey: string) {
  const origin = req.headers.get('origin');
  if (origin && origin !== (process.env.CONSULT_PUBLIC_ORIGIN || req.nextUrl.origin)) throw new CrossOriginConsultation('Cross-origin consultation mutation');
  const jar = await cookies();
  const old = jar.get('global-in-owner')?.value;
  const token = old && /^[a-f0-9]{64}$/.test(old) ? old : randomBytes(32).toString('hex');
  jar.set('global-in-owner', token, { httpOnly: true, sameSite: 'strict',
    secure: process.env.NODE_ENV === 'production', path: '/', maxAge: 86400 });
  return createHmac('sha256', process.env.CONSULT_OWNER_SECRET || apiKey).update(token).digest('hex');
}
