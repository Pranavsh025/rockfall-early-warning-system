import { useEffect, useRef } from 'react'
import mapboxgl from 'mapbox-gl'
import maplibregl from 'maplibre-gl'
import { LEVEL_COLORS, levelForScore } from '../api'

const TOKEN = import.meta.env.VITE_MAPBOX_TOKEN
// Mapbox when a token is provided, otherwise free OpenFreeMap tiles via MapLibre (same API)
const lib = TOKEN ? mapboxgl : maplibregl
if (TOKEN) mapboxgl.accessToken = TOKEN
const STYLE = TOKEN ? 'mapbox://styles/mapbox/light-v11' : 'https://tiles.openfreemap.org/styles/positron'

// Used when the tile server can't be reached (offline / firewall) so markers still render
const FALLBACK_STYLE = {
  version: 8,
  sources: {},
  layers: [{ id: 'bg', type: 'background', paint: { 'background-color': '#efe4d6' } }],
}

const colorExpr = [
  'match', ['get', 'level'],
  'CRITICAL', LEVEL_COLORS.CRITICAL,
  'HIGH', LEVEL_COLORS.HIGH,
  'MODERATE', LEVEL_COLORS.MODERATE,
  LEVEL_COLORS.LOW,
]

function toGeoJSON(mines) {
  const features = []
  for (const m of mines) {
    features.push({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [m.lng, m.lat] },
      properties: { kind: 'mine', id: m.id, name: m.name, score: m.overall_score, level: m.risk_level },
    })
    for (const z of m.zones || []) {
      features.push({
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [z.lng, z.lat] },
        properties: { kind: 'zone', id: m.id, name: `${m.name} · ${z.name}`, score: z.score, level: levelForScore(z.score) },
      })
    }
  }
  return { type: 'FeatureCollection', features }
}

/**
 * Map of monitored mines. `interactive=false` renders it as a decorative,
 * sepia-toned background (Assessment view); otherwise it is the live risk map.
 */
export default function MapCanvas({ mines, selectedId, onSelect, interactive = true, className = '' }) {
  const ref = useRef(null)
  const mapRef = useRef(null)
  const readyRef = useRef(false)
  const onSelectRef = useRef(onSelect)
  onSelectRef.current = onSelect

  useEffect(() => {
    const map = new lib.Map({
      container: ref.current,
      style: STYLE,
      center: [81.5, 21.5],
      zoom: interactive ? 4.1 : 4.6,
      interactive,
      attributionControl: interactive,
    })
    mapRef.current = map
    if (interactive) map.addControl(new lib.NavigationControl({ showCompass: false }), 'top-right')

    let fellBack = false
    map.on('error', () => {
      if (!fellBack && !readyRef.current && !map.isStyleLoaded()) {
        fellBack = true
        map.setStyle(FALLBACK_STYLE)
      }
    })

    map.on('load', () => {
      map.addSource('mines', { type: 'geojson', data: toGeoJSON([]) })
      map.addLayer({
        id: 'mine-halo',
        type: 'circle',
        source: 'mines',
        filter: ['==', ['get', 'kind'], 'mine'],
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['get', 'score'], 0, 10, 100, 26],
          'circle-color': colorExpr,
          'circle-opacity': 0.18,
        },
      })
      map.addLayer({
        id: 'mine-dot',
        type: 'circle',
        source: 'mines',
        filter: ['==', ['get', 'kind'], 'mine'],
        paint: {
          'circle-radius': ['case', ['==', ['get', 'id'], selectedId || ''], 9, 7],
          'circle-color': colorExpr,
          'circle-stroke-color': '#fff',
          'circle-stroke-width': 2,
        },
      })
      map.addLayer({
        id: 'zone-dot',
        type: 'circle',
        source: 'mines',
        minzoom: 11,
        filter: ['==', ['get', 'kind'], 'zone'],
        paint: { 'circle-radius': 14, 'circle-color': colorExpr, 'circle-opacity': 0.55, 'circle-stroke-color': '#fff', 'circle-stroke-width': 1.5 },
      })
      if (interactive && map.getStyle().glyphs) {
        map.addLayer({
          id: 'mine-label',
          type: 'symbol',
          source: 'mines',
          filter: ['==', ['get', 'kind'], 'mine'],
          layout: {
            'text-field': ['concat', ['get', 'name'], '\n', ['to-string', ['get', 'score']], '%'],
            'text-size': 11,
            'text-offset': [0, 1.6],
            'text-anchor': 'top',
            'text-font': TOKEN ? ['DIN Pro Medium', 'Arial Unicode MS Regular'] : ['Noto Sans Regular'],
          },
          paint: { 'text-color': '#4a2f18', 'text-halo-color': '#fff', 'text-halo-width': 1.4 },
        })
      }
      if (interactive) {
        const popup = new lib.Popup({ closeButton: false, closeOnClick: false, offset: 12 })
        for (const layer of ['mine-dot', 'zone-dot']) {
          map.on('click', layer, (e) => onSelectRef.current?.(e.features[0].properties.id))
          map.on('mouseenter', layer, (e) => {
            map.getCanvas().style.cursor = 'pointer'
            const p = e.features[0].properties
            popup.setLngLat(e.lngLat).setHTML(`<b>${p.name}</b><br/>${p.level} · ${p.score}%`).addTo(map)
          })
          map.on('mouseleave', layer, () => {
            map.getCanvas().style.cursor = ''
            popup.remove()
          })
        }
      }
      readyRef.current = true
      map.getSource('mines').setData(toGeoJSON(mapRef.current._minesCache || []))
    })
    return () => map.remove()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [interactive])

  // push live data into the map
  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    map._minesCache = mines
    if (readyRef.current) map.getSource('mines')?.setData(toGeoJSON(mines))
  }, [mines])

  // highlight + fly to the selected mine
  useEffect(() => {
    const map = mapRef.current
    if (!map || !selectedId) return
    const m = mines.find((x) => x.id === selectedId)
    if (readyRef.current && map.getLayer('mine-dot')) {
      map.setPaintProperty('mine-dot', 'circle-radius', ['case', ['==', ['get', 'id'], selectedId], 10, 7])
    }
    if (m) map.flyTo({ center: [m.lng + (interactive ? 0 : 4), m.lat], zoom: interactive ? map.getZoom() : 4.6, speed: 0.8 })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId, mines.length])

  return <div ref={ref} className={`map-canvas ${className}`} />
}
