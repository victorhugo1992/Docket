
class SecuenciaLogica:
    def __init__(self):
        # Variable global de la clase equivalente a listaOrdenconexion en C#
        self.lista_orden_conexion = [] 

    def crear_secuencia_ordenada_db2(self, conexion: list, conexion_ordenada: list, taladros: list) -> list:
        if not conexion:
            return []

        # 1. Aplanar la lista de conexiones
        conexiones_planas = [con for rama in conexion for con in rama]

        # 2. Extraer los IDs de taladros marcados como inicio
        ids_taladro_hole1 = [
            c.get("hole1", {}).get("id_taladro") 
            for c in conexiones_planas 
            if c.get("hole1") and c.get("hole1").get("is_inicio")
        ]
        
        ids_taladro_hole2 = [
            c.get("hole2", {}).get("id_taladro") 
            for c in conexiones_planas 
            if c.get("hole2") and c.get("hole2").get("is_inicio")
        ]

        # Juntar y obtener valores únicos preservando el orden
        ids_taladro_todos = [id_t for id_t in (ids_taladro_hole1 + ids_taladro_hole2) if id_t is not None]
        _ids_taladro = list(dict.fromkeys(ids_taladro_todos)) 

        for tm_id in _ids_taladro:
            # Buscar el taladro correspondiente
            tm = next((t for t in taladros if t.get("id_taladro") == tm_id), None)
            
            if tm and tm.get("id_taladro", 0) > 0:
                index = self.verificar_ramal(conexion_ordenada, tm_id)
                lista_superficie = self.found_superficie_secuencia(conexion, tm_id)
                ramal = []

                # Verificar si el taladro de inicio ya pertenece a un ramal en las crudas
                index_ramal = self.verificar_ramal(conexion, tm_id)

                # Bucle anidado para apagar las banderas is_inicio
                for i in index:
                    for j in range(len(conexion_ordenada[i])):
                        for k in range(len(conexion)):
                            for l in range(len(conexion[k])):
                                ho1_ord = conexion_ordenada[i][j].get("hole1", {})
                                ho2_ord = conexion_ordenada[i][j].get("hole2", {})
                                ho1_con = conexion[k][l].get("hole1", {})
                                ho2_con = conexion[k][l].get("hole2", {})
                                
                                id_evaluar = ho1_con.get("id_taladro")
                                if ho1_ord.get("id_taladro") == id_evaluar or ho2_ord.get("id_taladro") == id_evaluar:
                                    ho1_ord["is_inicio"] = False
                                    ho2_ord["is_inicio"] = False
                                    ho1_con["is_inicio"] = False
                                    ho2_con["is_inicio"] = False

                self.lista_orden_conexion.clear()

                # Si le pertenece a un ramal, limpiar
                if len(index) > 0:
                    for idx in index_ramal:
                        for con in conexion[idx]:
                            if "hole1" in con: con["hole1"]["is_inicio"] = False
                            if "hole2" in con: con["hole2"]["is_inicio"] = False
                    
                    # Eliminar de atrás hacia adelante para no corromper los índices
                    for idx in sorted(index, reverse=True):
                        conexion_ordenada.pop(idx)

                # Volver a marcar el taladro actual como inicio
                for rama in conexion:
                    for con in rama:
                        if con.get("hole1", {}).get("id_taladro") == tm_id:
                            con["hole1"]["is_inicio"] = True
                        elif con.get("hole2", {}).get("id_taladro") == tm_id:
                            con["hole2"]["is_inicio"] = True

                # Construir recursivamente los ramales a partir de la superficie
                for sup in lista_superficie:
                    self.crear_ramales(conexion, sup.get("id_conexion"), ramal, tm_id)

                conexion_ordenada.append(ramal)

        return conexion_ordenada

    def verificar_ramal(self, cm: list, tm_id: int) -> list:
        """Devuelve índices únicos donde se encuentra el taladro."""
        index = []
        for i, rama in enumerate(cm):
            for con in rama:
                ho1_id = con.get("hole1", {}).get("id_taladro")
                ho2_id = con.get("hole2", {}).get("id_taladro")
                
                if ho1_id == tm_id or ho2_id == tm_id:
                    index.append(i)
                    
        return list(dict.fromkeys(index))

    def found_superficie_secuencia(self, conexion: list, id_taladro: int) -> list:
        """Busca todas las conexiones que tocan un taladro específico."""
        lista_superficie = []
        for item in conexion:
            for i in range(len(item)):
                ho1_id = item[i].get("hole1", {}).get("id_taladro")
                ho2_id = item[i].get("hole2", {}).get("id_taladro")
                
                if ho1_id == id_taladro:
                    lista_superficie.append(item[i])
                elif ho2_id == id_taladro:
                    lista_superficie.append(item[i])
                    
        return lista_superficie

    def crear_ramales(self, conexion: list, id_conexion: int, ramal: list, id_taladro: int):
        """Función recursiva que recorre el grafo de detonadores ordenando la dirección."""
        for i in range(len(conexion)):
            for j in range(len(conexion[i])):
                dtp1 = {}
                dtp2 = {}
                
                # Verificar si la conexión ya fue procesada
                res = False
                for k in range(len(self.lista_orden_conexion)):
                    if id_conexion == self.lista_orden_conexion[k]:
                        res = True
                        break
                        
                if not res:
                    con_actual = conexion[i][j]
                    if id_conexion == con_actual.get("id_conexion"):
                        
                        ho1 = con_actual.get("hole1", {})
                        ho2 = con_actual.get("hole2", {})
                        
                        # Si el flujo va de Hole1 a Hole2
                        if ho1.get("id_taladro") == id_taladro:
                            res1 = self.taladro_repetido_secuencia_ordenada(ramal, ho1.get("id_taladro"))
                            ho1["is_repetido"] = res1
                            dtp1 = ho1
                            
                            res2 = self.taladro_repetido_secuencia_ordenada(ramal, ho2.get("id_taladro"))
                            ho2["is_repetido"] = res2
                            dtp2 = ho2
                            
                        # Si el flujo va de Hole2 a Hole1 (INVERTIMOS EL ORDEN)
                        elif ho2.get("id_taladro") == id_taladro:
                            res1 = self.taladro_repetido_secuencia_ordenada(ramal, ho2.get("id_taladro"))
                            ho2["is_repetido"] = res1
                            dtp1 = ho2  # Pasamos Hole2 a ser el Inicio (dtp1)
                            
                            res2 = self.taladro_repetido_secuencia_ordenada(ramal, ho1.get("id_taladro"))
                            ho1["is_repetido"] = res2
                            dtp2 = ho1  # Pasamos Hole1 a ser el Destino (dtp2)
                            
                        # Crear la nueva conexión orientada
                        _cm = {
                            "hole1": dtp1,
                            "hole2": dtp2,
                            "color": con_actual.get("color"),
                            "tiempo_taladro": con_actual.get("tiempo_taladro"),
                            "isconvencional": con_actual.get("isconvencional"),
                            "isDual": con_actual.get("isDual"),
                            "id_conexion": con_actual.get("id_conexion") # Aseguramos guardar el ID
                        }
                        
                        self.lista_orden_conexion.append(con_actual.get("id_conexion"))
                        ramal.append(_cm)
                        
                        # Llamada recursiva para seguir el cable desde el destino (dtp2)
                        _lista_superficie = self.found_superficie_secuencia(conexion, dtp2.get("id_taladro"))
                        
                        for k in range(len(_lista_superficie)):
                            self.crear_ramales(conexion, _lista_superficie[k].get("id_conexion"), ramal, dtp2.get("id_taladro"))

    def taladro_repetido_secuencia_ordenada(self, ramal: list, id_taladro: int) -> bool:
        """
        Esta función no estaba en el código C#, pero por su nombre y uso,
        evalúa si el taladro ya existe en el ramal actual.
        """
        for con in ramal:
            if con.get("hole1", {}).get("id_taladro") == id_taladro:
                return True
            if con.get("hole2", {}).get("id_taladro") == id_taladro:
                return True
        return False

def calcular_isocronas(conexiones_planas, inicios_ids):
    """
    Calcula el tiempo real acumulado (ms) para cada taladro (Isocronas).
    Usa un algoritmo de grafos para sumar los tiempos desde los arranques.
    """
    import collections
    tiempos_acumulados = {}
    
    # 1. Armamos el grafo dirigido con los datos ya ordenados
    grafo = collections.defaultdict(list)
    for con in conexiones_planas:
        # Extraemos los IDs asegurándonos de que sean cadenas de texto
        u = str(con.get("hole1", {}).get("id_taladro"))
        v = str(con.get("hole2", {}).get("id_taladro"))
        t = float(con.get("tiempo_taladro", 0))
        
        # Agregamos la ruta del cable y su tiempo de retardo
        grafo[u].append((v, t))

    # 2. Iniciar la onda de detonación desde los arranques (Tiempo = 0 ms)
    queue = collections.deque()
    for ini in inicios_ids:
        ini_str = str(ini)
        tiempos_acumulados[ini_str] = 0.0
        queue.append(ini_str)

    # 3. Propagar y sumar tiempos (Búsqueda del camino más rápido / Dijkstra)
    while queue:
        actual = queue.popleft()
        t_actual = tiempos_acumulados[actual]

        # Revisamos todos los cables que salen del taladro actual
        for vecino, delay in grafo.get(actual, []):
            nuevo_t = t_actual + delay
            
            # Si el taladro vecino aún no tiene tiempo, o si llegamos a él 
            # de forma más rápida por otra conexión (física real), lo actualizamos
            if vecino not in tiempos_acumulados or nuevo_t < tiempos_acumulados[vecino]:
                tiempos_acumulados[vecino] = nuevo_t
                queue.append(vecino)
                
    return tiempos_acumulados

def agrupar_conexiones_por_lista(conexiones_planas):
    """Agrupa una lista plana de conexiones en sublistas basándose en el 'idlista'."""
    from itertools import groupby
    conexiones_ordenadas = sorted(conexiones_planas, key=lambda x: x.get("idlista", 0))
    conexiones_agrupadas = []
    for key, group in groupby(conexiones_ordenadas, key=lambda x: x.get("idlista", 0)):
        conexiones_agrupadas.append(list(group))
    return conexiones_agrupadas

def vincular_detonadores_a_conexiones(lista_conexiones, lista_detonadores):
    for conexion in lista_conexiones:
        id_con = conexion.get("id_conexion")
        detonadores_match = [d for d in lista_detonadores if d.get("id_conexion") == id_con]
        if len(detonadores_match) > 0:
            conexion["hole1"] = detonadores_match[0]
        if len(detonadores_match) > 1:
            conexion["hole2"] = detonadores_match[1]
    return lista_conexiones