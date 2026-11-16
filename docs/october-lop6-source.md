# October 2026 grade-6 offer provenance

- Official source: https://tak12.com/news/n/2499/tang-khoa-luyen-de-vao-6-cho-hoc-vien-tak12
- Retrieved: 2026-10-14T04:19:54Z (UTC), equivalent to 2026-10-14 11:19:54 Asia/Ho_Chi_Minh (UTC+07:00).
- Fetch: HTTP 200 via `curl -fL`; source Article schema reports `dateModified: 2026-10-12T20:03:18Z`.
- SHA-256 of the fetched response body: `d6570b21bbd3bbf0ea015420ba0bb5e92751f5686e01603e3d82543c9d6ad65d`.
- Response body was inspected in the Hermes scratch cache; the large HTML artifact is not archived in the repository. The digest identifies that retrieval, not future responses.

## Refreshed source check (2026-11-16)

- Retrieved: 2026-11-16 UTC with HTTP 200.
- SHA-256 of the fetched response body: `ea3ca465b19296a0fee80d9513a5600008aa3bb9d0af4063f2e135dbd8edb3e9`.
- Article schema reports `dateModified: 2026-11-01T18:28:36Z`.
- The current source still states 18 sessions beginning 09/11/2026 and running across November, December 2026, and January 2027, but no longer states the exact end date 23/01/2027. Public copy must not retain that unsupported endpoint.

## Verified facts

- Offer runs from 08/10 through the end of 31/10/2026, Vietnam time.
- Qualifying purchase is either **Trọn bộ ôn thi vào 6** for students in grades **3, 4, 5**, or **Combo Luyện đề 3 môn 12 trường THCS CLC** for students in grades **4, 5**.
- Benefit is the added **Thi thử vào 6** program. Its duration matches the duration of the activated practice package.
- The separate live practice course has 18 sessions beginning 09/11/2026, for students with an unexpired grade-6 PRO practice package; the Thi thử vào 6 package alone does not qualify for that course. Existing coverage of that course remains unchanged.

## Publication boundary

The homepage discovery slot and grade-6 pillar section start with `hidden` and reuse the existing `data-dated-offer` countdown. End date `31/10/2026` resolves to exclusive expiry **2026-11-01T00:00:00+07:00**, or **2026-10-31T17:00:00Z**, independent of the visitor's timezone. Expired and no-JavaScript visits keep the offer hidden. Existing timer, visibilitychange and pageshow handlers recheck long-open tabs.

Only visible-page campaign copy contains the dated offer; metadata, JSON-LD and llms.txt are unchanged. Pricing links use the existing grade-6 affiliate route with `exam_grade_6` intent; official-source links use `verify-offer-terms`. Both carry the existing referral code and sponsored/noopener semantics, with unique CTA IDs.
