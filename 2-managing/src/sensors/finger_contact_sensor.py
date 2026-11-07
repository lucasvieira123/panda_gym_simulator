from ._sensor import _Sensor

_FINGER_JOINT_NAMES = {b"panda_finger_joint1", b"panda_finger_joint2"}
_NORMAL_FORCE       = 9  # índice em getContactPoints
_LATERAL_FRICTION   = 1  # índice em getDynamicsInfo


class FingerContactSensor(_Sensor):
    """
    Detecta quantos dedos do gripper estão em contato físico com o objeto alvo,
    usando PyBullet getContactPoints — sem proxies de distância ou largura.

    Retorna:
        finger_contacts: 0, 1 ou 2
        finger_normal_forces: força normal total (N) em cada dedo
        finger_lateral_friction: atrito lateral atual de cada dedo

    Só lê o estado da simulação, sem alterar a dinâmica.
    """

    def __init__(self, configs: dict, sim, object_name: str = "object_1") -> None:
        super().__init__(configs)
        self._object_name  = object_name
        self._panda_id     = sim._bodies_idx["panda"]
        self._finger_links = self._find_finger_links(sim.physics_client)

    def _find_finger_links(self, physics_client) -> list[int]:
        """Descobre os link indices dos dedos pelo nome da joint no URDF."""
        links = []
        num_joints = physics_client.getNumJoints(self._panda_id)
        for i in range(num_joints):
            info = physics_client.getJointInfo(self._panda_id, i)
            if info[1] in _FINGER_JOINT_NAMES:
                links.append(i)
        return links

    def sense(self, simulation, robot, environment, obs: dict) -> dict:
        obj_id = simulation._bodies_idx.get(self._object_name)
        if obj_id is None or not self._finger_links:
            return {"finger_contacts": 0}

        pc       = simulation.physics_client
        contacts = [
            pc.getContactPoints(bodyA=self._panda_id, bodyB=obj_id, linkIndexA=link)
            for link in self._finger_links
        ]
        return {
            "finger_contacts":         sum(1 for points in contacts if points),
            "finger_normal_forces":    [float(sum(p[_NORMAL_FORCE] for p in points)) for points in contacts],
            "finger_lateral_friction": [float(pc.getDynamicsInfo(self._panda_id, link)[_LATERAL_FRICTION])
                                        for link in self._finger_links],
        }
