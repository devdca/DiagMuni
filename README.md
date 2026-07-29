# DiagMuni

Plataforma open source de diagnóstico y modelado de la modernización municipal, del Laboratorio de Innovación Pública del INAP.

DiagMuni permite a un gobierno local (municipio en México, intendencia en Uruguay) autodiagnosticar su nivel de madurez digital trámite por trámite y recibir un plan de modernización a la medida: tecnología a adoptar, inversión estimada, personal y capacitación requeridos.

Principio rector: **motor determinista primero, IA después**. El índice de madurez y las reglas normativas son código puro, testeable y reproducible; los modelos de lenguaje solo redactan el plan en lenguaje natural, clasifican texto libre y asisten la captura.

Proyecto presentado a **GovTech Connect** (BID Lab / Red de Innovación Local), piloto de código abierto en una ciudad de la coalición CIIAR Uruguay.

## Estado

En desarrollo temprano — sin release todavía. Motor determinista, modelo de datos y API REST del backend ya funcionan (ver `backend/`); la capa de IA (F1/F3/F9) y las pantallas del frontend están pendientes.

## Cómo correr el proyecto

```
cp .env.example .env
docker compose up -d
```

Documentación técnica completa en `docs/` (producto, arquitectura, esquema de datos, flujo de la aplicación) y `entregables/` (catálogo normativo del motor de diagnóstico, teoría de cambio).

## Licencia

[Apache License 2.0](LICENSE) — ver también [NOTICE](NOTICE). Toda dependencia debe tener licencia compatible (MIT, BSD, Apache); GPL solo como servicio independiente sin linking de código; AGPL nunca como dependencia integrada.

## Transferencia de capacidades

El código, los datos y el diagnóstico generado pertenecen al gobierno local que los produce. DiagMuni no genera dependencia de su implementador original: despliegue por contenedores, documentación técnica desde el primer commit, sin componentes privativos.
