import assert from 'node:assert/strict'
import test from 'node:test'

import { countLabel, emptyLabel } from './labels.js'

test('검색 중이 아니면 건수만 보여준다', () => {
  assert.equal(countLabel({ count: 33 }), '33명')
})

test('검색어와 건수를 함께 보여준다', () => {
  assert.equal(countLabel({ count: 1, query: '하늘' }), '"하늘" 검색 결과 1명')
})

test('위험도 필터가 걸려 있으면 같이 알린다', () => {
  assert.equal(countLabel({ count: 2, filter: 'CRITICAL' }), '2명 · 심각 필터 적용 중')
  assert.equal(
    countLabel({ count: 1, query: '하늘', filter: 'CAUTION' }),
    '"하늘" 검색 결과 1명 · 주의 필터 적용 중',
  )
})

test('결과가 없으면 건수 문구를 만들지 않는다', () => {
  // 화면은 이 자리를 빈 줄로 유지한다. 줄을 없애면 아래 내용이 밀려 올라온다.
  assert.equal(countLabel({ count: 0, query: '하늘' }), '')
})

test('앞뒤 공백은 문구에 새지 않는다', () => {
  assert.equal(countLabel({ count: 1, query: '  하늘  ' }), '"하늘" 검색 결과 1명')
  assert.equal(countLabel({ count: 5, query: '   ' }), '5명')
})

test('검색 결과 없음과 필터 결과 없음을 구분한다', () => {
  // 같은 문구를 쓰면 검색어를 고쳐야 하는지 필터를 풀어야 하는지 알 수 없다.
  assert.equal(emptyLabel({}), '해당하는 대상자가 없습니다.')
  assert.equal(
    emptyLabel({ query: '하늘' }),
    '"하늘"에 해당하는 대상자가 없습니다.',
  )
  assert.equal(
    emptyLabel({ query: '하늘', filter: 'NORMAL' }),
    '"하늘"에 해당하는 대상자가 없습니다. 안정 필터를 풀고 다시 찾아보세요.',
  )
})

test('검색어가 없으면 필터가 걸려 있어도 필터 안내를 덧붙이지 않는다', () => {
  // 필터만 걸고 결과가 0이면 필터를 바꾸는 것 말고 할 게 없어 안내가 군더더기다.
  assert.equal(emptyLabel({ filter: 'CRITICAL' }), '해당하는 대상자가 없습니다.')
})
