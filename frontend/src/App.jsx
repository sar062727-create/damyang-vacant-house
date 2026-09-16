import { useEffect, useRef, useState } from 'react'
import './App.css'

const API_BASE = 'http://127.0.0.1:8000'

const USAGE_LIST = [
  { key: '주거점수', label: '주거', icon: '🏠' },
  { key: '카페소품샵점수', label: '카페·소품샵', icon: '☕' },
  { key: '게스트하우스펜션점수', label: '게스트하우스·펜션', icon: '🏡' },
  { key: '식당베이커리점수', label: '식당·베이커리', icon: '🍞' },
]

// "이름|위도|경도;;이름|위도|경도" 형태 문자열을 파싱
function parsePlaces(str) {
  if (!str) return []
  return str
    .split(';;')
    .map((entry) => {
      const [name, lat, lon] = entry.split('|')
      if (!name || !lat || !lon) return null
      return { name, lat: parseFloat(lat), lon: parseFloat(lon) }
    })
    .filter(Boolean)
}

function DecisionCard({ house, onClose }) {
  const mapRef = useRef(null)

  useEffect(() => {
    if (!window.kakao || !window.kakao.maps || !mapRef.current) return

    window.kakao.maps.load(() => {
      // 비동기 콜백이 실행되는 시점엔 카드가 이미 닫혔을 수도 있으므로 다시 확인
      if (!mapRef.current) return

      const center = new window.kakao.maps.LatLng(house.위도, house.경도)
      const map = new window.kakao.maps.Map(mapRef.current, {
        center,
        level: 6,
      })

      // 빈집 위치 (빨간 마커)
      new window.kakao.maps.Marker({ position: center, map })

      // 반경 3km 원
      new window.kakao.maps.Circle({
        center,
        radius: 3000,
        strokeWeight: 1,
        strokeColor: '#2C5F2D',
        strokeOpacity: 0.6,
        fillColor: '#2C5F2D',
        fillOpacity: 0.08,
        map,
      })

      // 주변 관광명소 (주황 점)
      const attractions = parsePlaces(house.관광명소좌표)
      attractions.forEach((p) => {
        const marker = new window.kakao.maps.Marker({
          position: new window.kakao.maps.LatLng(p.lat, p.lon),
          map,
          image: new window.kakao.maps.MarkerImage(
            'data:image/svg+xml;base64,' +
              btoa(
                '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12"><circle cx="6" cy="6" r="5" fill="#D85A30" fill-opacity="0.85"/></svg>'
              ),
            new window.kakao.maps.Size(12, 12)
          ),
        })
        const iw = new window.kakao.maps.InfoWindow({
          content: `<div style="padding:4px 8px;font-size:11px;">${p.name}</div>`,
        })
        window.kakao.maps.event.addListener(marker, 'click', () => iw.open(map, marker))
      })

      // 주변 학교 (파란 점)
      const schools = parsePlaces(house.학교좌표)
      schools.forEach((p) => {
        const marker = new window.kakao.maps.Marker({
          position: new window.kakao.maps.LatLng(p.lat, p.lon),
          map,
          image: new window.kakao.maps.MarkerImage(
            'data:image/svg+xml;base64,' +
              btoa(
                '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12"><circle cx="6" cy="6" r="5" fill="#378ADD" fill-opacity="0.85"/></svg>'
              ),
            new window.kakao.maps.Size(12, 12)
          ),
        })
        const iw = new window.kakao.maps.InfoWindow({
          content: `<div style="padding:4px 8px;font-size:11px;">${p.name}</div>`,
        })
        window.kakao.maps.event.addListener(marker, 'click', () => iw.open(map, marker))
      })
    })
  }, [house])

  const attractionNames = house.관광명소목록 ? house.관광명소목록.split(', ') : []
  const attractionExtra = Math.max(0, (house.관광명소수 || 0) - attractionNames.length)

  return (
    <div className="card-overlay" onClick={onClose}>
      <div className="decision-card" onClick={(e) => e.stopPropagation()}>
        <button className="card-close" onClick={onClose}>×</button>

        <div className="card-header">
          <div className="card-photo-placeholder">사진</div>
          <div>
            <p className="card-address">{house['위치주소(지번 비공개)']}</p>
            <p className="card-sub">{house.주택유형} · {house.조사년도}년 조사 · {house.빈집유형}</p>
          </div>
        </div>

        <p className="card-section-title">용도별 적합도 (담양군 내 상대 점수)</p>
        <div className="usage-bars">
          {USAGE_LIST.map((u) => {
            const score = house[u.key] || 0
            const isTop = house['1위용도'] === u.label.replace('·', '').replace(' ', '')
              || (u.key === '주거점수' && house['1위용도'] === '주거')
              || (u.key === '카페소품샵점수' && house['1위용도'] === '카페소품샵')
              || (u.key === '게스트하우스펜션점수' && house['1위용도'] === '게스트하우스펜션')
              || (u.key === '식당베이커리점수' && house['1위용도'] === '식당베이커리')
            return (
              <div key={u.key} className="usage-bar-row">
                <div className={`usage-bar-label ${isTop ? 'top' : ''}`}>
                  <span>{u.icon} {u.label}</span>
                  <span>{score}점</span>
                </div>
                <div className="usage-bar-track">
                  <div
                    className={`usage-bar-fill ${isTop ? 'top' : ''}`}
                    style={{ width: `${score}%` }}
                  />
                </div>
              </div>
            )
          })}
        </div>

        {house['1위용도근거'] && (
          <div className="reason-banner">💡 {house['1위용도근거']}</div>
        )}

        <p className="card-section-title">읍면 현황</p>
        <div className="stat-grid">
          <div className="stat-box">
            <p className="stat-label">{house.읍면} 인구</p>
            <p className="stat-value">{Number(house.인구수).toLocaleString()}명</p>
          </div>
          <div className="stat-box">
            <p className="stat-label">유동인구 수준(추정)</p>
            <p className="stat-value">{house['유동인구수준(추정)']} <span className="stat-sub">({house['유동인구순위(추정)']})</span></p>
          </div>
        </div>

        {attractionNames.length > 0 && (
          <>
            <p className="card-section-title">주변 관광명소 (반경 3km, 총 {house.관광명소수}곳)</p>
            <div className="tag-list">
              {attractionNames.map((n, i) => (
                <span key={i} className="tag tag-attraction">{n}</span>
              ))}
              {attractionExtra > 0 && <span className="tag tag-muted">외 {attractionExtra}곳</span>}
            </div>
          </>
        )}

        <p className="card-section-title">지도로 보기</p>
        <div ref={mapRef} className="mini-map" />
        <div className="mini-map-legend">
          <span><span className="dot dot-red" /> 이 빈집</span>
          <span><span className="dot dot-orange" /> 관광명소</span>
          <span><span className="dot dot-blue" /> 학교</span>
        </div>

        <div className="card-footer">
          <span>철거/활용 동의: {house['철거 또는 활용동의']}</span>
        </div>
      </div>
    </div>
  )
}

function App() {
  const mapRef = useRef(null)
  const mapObjRef = useRef(null)
  const markersRef = useRef([])

  const [houses, setHouses] = useState([])
  const [filter, setFilter] = useState('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [mapReady, setMapReady] = useState(false)
  const [selectedHouse, setSelectedHouse] = useState(null)

  useEffect(() => {
    fetch(`${API_BASE}/houses`)
      .then((res) => {
        if (!res.ok) throw new Error(`서버 응답 오류: ${res.status}`)
        return res.json()
      })
      .then((data) => {
        setHouses(data.houses)
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
  }, [])

  useEffect(() => {
    // loading이 true인 동안에는 <div ref={mapRef}>가 화면에 렌더링되지 않아
    // mapRef.current가 null이므로, loading이 끝난 뒤에 다시 시도하도록
    // 의존성 배열에 loading을 넣는다.
    if (loading || !window.kakao || !window.kakao.maps || !mapRef.current) return
    window.kakao.maps.load(() => {
      if (!mapRef.current) return
      const center = new window.kakao.maps.LatLng(35.29, 126.99)
      const map = new window.kakao.maps.Map(mapRef.current, { center, level: 9 })
      mapObjRef.current = map
      setMapReady(true)
    })
  }, [loading])

  useEffect(() => {
    if (!mapReady || houses.length === 0) return

    markersRef.current.forEach((m) => m.setMap(null))
    markersRef.current = []

    const filtered =
      filter === 'all' ? houses : houses.filter((h) => h['1위용도'] === filter)

    filtered.forEach((h) => {
      const position = new window.kakao.maps.LatLng(h.위도, h.경도)
      const marker = new window.kakao.maps.Marker({ position, map: mapObjRef.current })
      window.kakao.maps.event.addListener(marker, 'click', () => setSelectedHouse(h))
      markersRef.current.push(marker)
    })
  }, [mapReady, houses, filter])

  if (loading) return <div className="status-message">빈집 데이터를 불러오는 중입니다...</div>
  if (error) {
    return (
      <div className="status-message error">
        데이터를 불러오지 못했습니다: {error}
        <br />
        FastAPI 서버(uvicorn main:app --reload)가 켜져 있는지 확인해주세요.
      </div>
    )
  }

  const filteredCount =
    filter === 'all' ? houses.length : houses.filter((h) => h['1위용도'] === filter).length

  return (
    <div className="app">
      <h1>담양군 빈집 입지 분석 및 용도 추천</h1>
      <p className="subtitle">총 {houses.length}건 · 현재 표시 {filteredCount}건 · 마커를 클릭하면 상세 카드가 열립니다</p>

      <div className="filters">
        <button className={filter === 'all' ? 'active' : ''} onClick={() => setFilter('all')}>전체</button>
        <button className={filter === '주거' ? 'active' : ''} onClick={() => setFilter('주거')}>주거</button>
        <button className={filter === '카페소품샵' ? 'active' : ''} onClick={() => setFilter('카페소품샵')}>카페·소품샵</button>
        <button className={filter === '게스트하우스펜션' ? 'active' : ''} onClick={() => setFilter('게스트하우스펜션')}>게스트하우스·펜션</button>
        <button className={filter === '식당베이커리' ? 'active' : ''} onClick={() => setFilter('식당베이커리')}>식당·베이커리</button>
      </div>

      <div ref={mapRef} className="map" />

      {selectedHouse && (
        <DecisionCard house={selectedHouse} onClose={() => setSelectedHouse(null)} />
      )}
    </div>
  )
}

export default App
