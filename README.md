# IBM Global AI Racing League 2026 — Solo Entry by Alvaro

> Autonomous racing agent for **TORCS** built for the IBM Global AI Racing League.
> Circuit: **Corkscrew** · Car: `car1-trb1` (IBM / Granite livery) · Stack: Python + IBM Granite 4.0 (local via Ollama + Continue.dev)

---

## Resultados

| Intento | TARGET_SPEED | STEER_GAIN | CENTERING_GAIN | Freno | Mejor vuelta | Δ |
|---------|--------------|------------|----------------|-------|--------------|---|
| 1 (baseline) | 70 | 30 | 0.20 | 0.3 @ 0.9 rad | **03:04.55** | — |
| 2 | 75 | 30 | 0.20 | 0.6 @ 0.5 rad | **02:55.03** | −9.52 s |
| 3 | 75 | 35 | 0.30 | 0.6 @ 0.5 rad | **02:53.68** | −1.35 s |
| **4 (V2 LOOKAHEAD final)** | **70–120 din.** | **35** | **0.40** | **progresivo** | **02:27.28** | **−26.40 s** |

> **Mejora acumulada total:** −37.27 s (−20.20 %) · **Vuelta final entregable: 02:27.28**

---

## Enfoque técnico

Este agente no utiliza aprendizaje por refuerzo ni redes neuronales entrenadas. Está basado en una **política reactiva cuidadosamente ajustada** que lee los sensores de TORCS en cada frame y decide `steer`, `accel`, `brake` y `gear`. La filosofía es "entender primero la física, optimizar después": el objetivo fue conseguir un agente que complete vueltas limpias de forma consistente antes de intentar ir rápido.

### Bucle de decisión

1. **Lectura de sensores** — `angle`, `trackPos`, `speedX`, `rpm`, `wheelSpinVel`, y los 19 rayos de distancia `track[0..18]` que actúan como un LIDAR frontal.
2. **Dirección** — combinación lineal del ángulo del coche respecto al eje de la pista y la desviación lateral para mantener el coche centrado.
3. **Velocidad objetivo dinámica (V2)** — se calcula en cada tick a partir de la distancia frontal visible: mucho asfalto delante → acelerar hasta `MAX_SPEED`; poco asfalto → bajar hasta `MIN_SPEED`. La interpolación lineal entre ambos extremos es lo que permite pasar recta tras recta sin intervenir manualmente.
4. **Frenado progresivo** — proporcional al exceso de velocidad sobre el objetivo, con freno de emergencia si detecta obstáculo a menos de 25 m.
5. **Cambio de marchas con histéresis** — umbrales distintos para subir y bajar marcha según RPM, evitando oscilaciones cuando la velocidad ronda el umbral.
6. **Control de tracción** — reduce gas si las ruedas traseras patinan respecto a las delanteras.
7. **Recuperación automática** — si el coche se sale de pista (`|trackPos| > 1`), bloquea acelerador, frena y gira hacia el centro.

### Uso de IBM Granite 4.0

La competición exige uso del modelo Granite de IBM. En este proyecto Granite 4.0 350M se ejecuta **localmente vía Ollama** y se integra en VS Code mediante **Continue.dev**, actuando como copiloto durante el proceso iterativo de ajuste de parámetros. Granite se usa para:

- Proponer alternativas cuando un cambio de parámetro degrada el tiempo.
- Sugerir funciones auxiliares (como `get_curvature_hint()`) a partir de descripciones en lenguaje natural.
- Explicar el comportamiento de sensores de TORCS que no están documentados.
- Revisar el código antes de cada commit.

---

## Estructura del repositorio

```
.
├── README.md                         Este archivo
├── src/
│   ├── torcs_jm_par.py               Agente V1 (baseline ajustado, 2:53.68)
│   └── torcs_jm_par_V2_LOOKAHEAD.py  Agente V2 con lookahead dinámico
├── docs/
│   ├── Informe_Tecnico.docx          Documento técnico completo
│   └── Bitacora_TORCS_IBM_Racing.xlsx  Bitácora de experimentos
├── media/
│   ├── fastest_lap.mp4               Vídeo de vuelta rápida (entregable)
│   └── team_video.mp4                Vídeo de equipo (entregable)
└── livery/
    └── car1-trb1_custom.rgb          Livery personalizada IBM/Granite
```

---

## Instalación rápida

### Requisitos

- Windows 10/11, macOS o Linux
- Python 3.10+ (probado en 3.14.3)
- TORCS + SCR patch (entregados por IBM en `TORCSdownload.zip`)
- 4 GB RAM, 3 GB de disco

### Pasos

```powershell
# 1. Crear entorno virtual
python -m venv C:\torcs-env
C:\torcs-env\Scripts\Activate.ps1

# 2. Instalar dependencias
pip install numpy scipy scikit-learn torch gymnasium matplotlib pandas

# 3. Lanzar TORCS
Start-Process -FilePath C:\torcs\torcs\wtorcs.exe -WorkingDirectory C:\torcs\torcs

# 4. En TORCS: Race → Practice → seleccionar scr_server → New Race

# 5. En otra ventana PowerShell:
cd C:\torcs\gym_torcs
python torcs_jm_par.py
```

---

## Parámetros del V2

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `MIN_SPEED` | 70 | Velocidad objetivo mínima en curvas cerradas (km/h) |
| `MAX_SPEED` | 120 | Velocidad objetivo máxima en rectas largas (km/h) |
| `LOOKAHEAD_NEAR` | 30 | Distancia frontal que dispara MIN_SPEED (m) |
| `LOOKAHEAD_FAR` | 100 | Distancia frontal que dispara MAX_SPEED (m) |
| `STEER_GAIN` | 35 | Ganancia del volante |
| `CENTERING_GAIN` | 0.40 | Fuerza de centrado |
| `BRAKE_CURVE_FACTOR` | 0.8 | Intensidad de frenado proporcional |
| `EMERGENCY_BRAKE_DIST` | 25 | Distancia crítica para freno máximo (m) |

---

## Circuito: Corkscrew

Corkscrew es el circuito oficial de la clasificatoria. Tiene 11 curvas incluyendo una ese rápida y dos horquillas cerradas que penalizan fuertemente los agentes con mala gestión del freno. Es la prueba de fuego para un agente de conducción: no perdona exceso de velocidad en entrada.

Ruta del circuito: `torcs/tracks/road/corkscrew/`

---

## Licencia

Código del agente bajo MIT. Los assets de TORCS y del coche permanecen bajo sus respectivas licencias originales.

---

## Créditos

- **Autor**: Alvaro (participante solo)
- **Competición**: IBM Global AI Racing League 2026
- **Deadline**: 1 de julio de 2026
- **Modelo IA**: IBM Granite 4.0 350M via Ollama
- **Simulador**: TORCS + SCR patch
- **Starter kit**: `gym_torcs` provisto por IBM
