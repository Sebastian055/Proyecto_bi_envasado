

---

# **Resumen del Proyecto: Dashboard de Paros y Rendimiento (OEE)**

### **1. ¿Qué encontramos en los datos?**

* **La planta pasa parada el 38% del tiempo:** La disponibilidad está en **62,14%**, lo que significa que de cada 10 horas de turno, casi 4 se van en paros. Acumulamos **23.730 horas de paro** frente a **38.950 horas produciendo**.
* **El 80% del tiempo perdido son solo 3 problemas:** No hay que volverse locos arreglando 30 cosas. El Pareto nos muestra que casi todo el tiempo se pierde en:
1. **Aprovisionamiento y aseo del puesto:** $\approx 7.000$ horas perdidas.
2. **Ajustes operativos:** $\approx 5.000$ horas perdidas.
3. **Limpieza por derrames:** $\approx 5.000$ horas perdidas.


* **La línea que más produce es la que más sufre en arranques:** La línea **Vinilos_4** es la más rápida ($13,8\text{K}$ horas operadas), pero en **Enero y Diciembre** los paros se disparan feo en todas las líneas.

---

### **2. ¿Qué hay que hacer mañana en planta? (Plan de acción corto)**

1. **Atacar el aseo y la preparación de insumos:** Montar un estándar rápido para tener los insumos listos *antes* de que la máquina pare. Solo con eso nos ahorramos miles de horas.
2. **Evitar los derrames:** Revisar por qué se está tirando producto en línea para no perder tiempo limpiando a cada rato.
3. **Ponerle ojo a los arranques de año y fin de año:** Planear mantenimiento preventivo justo antes de Noviembre/Diciembre para que las máquinas no se queden paradas en plena temporada alta.

---

### **3. Lo que incluye la entrega técnica**

* Base de datos en **PostgreSQL** montada en modelo estrella (7 tablas bien conectadas).
* Dashboard interactivo en **Power BI** con filtros por Línea, Mes/Año y Operario.
* Medidas en **DAX** listas para OEE, Disponibilidad, Horas de Paro y el indicador de Pareto acumulado.
