import { useEffect, useRef, useState } from 'react'
import './App.css'

const API_BASE = 'http://127.0.0.1:8000'

const USAGE_COLORS = {
  '주거': '#378ADD',
  '관광·숙박(게스트하우스/카페)': '#D85A30',
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

  // 1. 빈집 데이터 불러오기 (FastAPI 백엔드)
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

  // 2. 카카오맵 SDK 로드 및 지도 초기화
  useEffect(() => {
    if (!window.kakao || !window.kakao.maps) {
      console.error('카카오맵 SDK를 불러오지 못했습니다. index.html의 appkey를 확인해주세요.')
      return
    }

    window.kakao.maps.load(() => {
      const center = new window.kakao.maps.LatLng(35.29, 126.99) // 담양군 대략 중심
      const map = new window.kakao.maps.Map(mapRef.current, {
        center,
        level: 9, // 숫자가 작을수록 확대됨
      })
      mapObjRef.current = map
      setMapReady(true)
    })
  }, [])

  // 3. 데이터 + 지도가 모두 준비되면 마커 그리기
  useEffect(() => {
    if (!mapReady || houses.length === 0) return

    // 기존 마커 제거 (필터 바뀔 때마다 다시 그림)
    markersRef.current.forEach((m) => m.setMap(null))
    markersRef.current = []

    const filteredHouses =
      filter === 'all' ? houses : houses.filter((h) => h.추천용도 === filter)

    filteredHouses.forEach((h) => {
      const position = new window.kakao.maps.LatLng(h.위도, h.경도)
      const color = USAGE_COLORS[h.추천용도] || '#888'

      // 색깔 있는 원형 커스텀 마커 (SVG를 이미지로 사용)
      const svgMarker = `
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16">
          <circle cx="8" cy="8" r="6" fill="${color}" fill-opacity="0.8" stroke="${color}" stroke-width="1"/>
        </svg>`
      const markerImage = new window.kakao.maps.MarkerImage(
        'data:image/svg+xml;base64,' + btoa(svgMarker),
        new window.kakao.maps.Size(16, 16)
      )

      const marker = new window.kakao.maps.Marker({
        position,
        image: markerImage,
        map: mapObjRef.current,
      })

      // 마커 클릭 시 정보창 표시
      const infowindow = new window.kakao.maps.InfoWindow({
        content: `<div style="padding:6px 10px;font-size:12px;">${h['위치주소(지번 비공개)']}<br/><b>${h.추천용도}</b></div>`,
      })
      window.kakao.maps.event.addListener(marker, 'click', () => {
        infowindow.open(mapObjRef.current, marker)
      })

      markersRef.current.push(marker)
    })
  }, [mapReady, houses, filter])

  if (loading) {
    return <div className="status-message">빈집 데이터를 불러오는 중입니다...</div>
  }

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
    filter === 'all' ? houses.length : houses.filter((h) => h.추천용도 === filter).length

  return (
    <div className="app">
      <h1>담양군 빈집 입지 분석 및 용도 추천</h1>
      <p className="subtitle">총 {houses.length}건 · 현재 표시 {filteredCount}건</p>

      <div className="filters">
        <button
          className={filter === 'all' ? 'active' : ''}
          onClick={() => setFilter('all')}
        >
          전체
        </button>
        <button
          className={filter === '주거' ? 'active' : ''}
          onClick={() => setFilter('주거')}
        >
          주거 적합
        </button>
        <button
          className={filter === '관광·숙박(게스트하우스/카페)' ? 'active' : ''}
          onClick={() => setFilter('관광·숙박(게스트하우스/카페)')}
        >
          관광·숙박 적합
        </button>
      </div>

      <div ref={mapRef} className="map" />

      <div className="legend">
        <span><span className="dot" style={{ background: USAGE_COLORS['주거'] }} /> 주거 적합</span>
        <span><span className="dot" style={{ background: USAGE_COLORS['관광·숙박(게스트하우스/카페)'] }} /> 관광·숙박 적합</span>
      </div>
    </div>
  )
}

export default App
