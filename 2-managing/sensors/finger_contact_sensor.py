from ._sensor import _Sensor

_FINGER_JOINT_NAMES = {b"panda_finger_joint1", b"panda_finger_joint2"}


class FingerContactSensor(_Sensor):
    """
    Detecta quantos dedos do gripper estão em contato físico com o objeto alvo,
    usando PyBullet getContactPoints — sem proxies de distância ou largura.

    Retorna:
        finger_contacts: 0, 1 ou 2
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

        pc    = simulation.physics_client
        count = sum(
            1 for link in self._finger_links
            if pc.getContactPoints(
                bodyA=self._panda_id,
                bodyB=obj_id,
                linkIndexA=link,
            )
        )
        return {"finger_contacts": count}
