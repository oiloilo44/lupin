"""플레이어 검색 및 관리 유틸리티"""

from typing import List, Optional, Tuple

from ..models import Player, Room


def find_player_by_session(
    rooms: dict[str, Room], session_id: str
) -> Optional[Tuple[Player, Room]]:
    """세션 ID로 플레이어 찾기

    Args:
        rooms: room_id -> Room 매핑 딕셔너리
        session_id: 찾고자 하는 세션 ID

    Returns:
        (Player, Room) 튜플 또는 None
    """
    if not session_id:
        return None

    for room in rooms.values():
        for player in room.players:
            if player.session_id == session_id:
                return player, room
    return None


def find_player_by_session_in_room(room: Room, session_id: str) -> Optional[Player]:
    """특정 방에서 세션 ID로 플레이어 찾기

    Args:
        room: 검색할 방
        session_id: 찾고자 하는 세션 ID

    Returns:
        Player 또는 None
    """
    if not session_id or not room:
        return None

    return room.find_player_by_session(session_id)


def find_player_by_number(room: Room, player_number: int) -> Optional[Player]:
    """플레이어 번호로 플레이어 찾기

    Args:
        room: 검색할 방
        player_number: 찾고자 하는 플레이어 번호

    Returns:
        Player 또는 None
    """
    if not room:
        return None

    for player in room.players:
        if player.player_number == player_number:
            return player
    return None


def get_opponent_player(room: Room, player_number: int) -> Optional[Player]:
    """상대방 플레이어 찾기

    Args:
        room: 검색할 방
        player_number: 현재 플레이어 번호

    Returns:
        상대방 Player 또는 None
    """
    if not room or len(room.players) < 2:
        return None

    for player in room.players:
        if player.player_number != player_number:
            return player
    return None


def get_opponent_by_session(room: Room, session_id: str) -> Optional[Player]:
    """세션 ID로 상대방 플레이어 찾기

    Args:
        room: 검색할 방
        session_id: 현재 플레이어의 세션 ID

    Returns:
        상대방 Player 또는 None
    """
    current_player = find_player_by_session_in_room(room, session_id)
    if not current_player:
        return None

    return get_opponent_player(room, current_player.player_number)


def find_player_by_session_or_number(room: Room, identifier: str) -> Optional[Player]:
    """세션 ID 또는 플레이어 번호로 플레이어 찾기

    Args:
        room: 검색할 방
        identifier: 세션 ID 문자열 또는 플레이어 번호 문자열

    Returns:
        Player 또는 None
    """
    if not room or not identifier:
        return None

    # 먼저 세션 ID로 찾기 시도
    player = find_player_by_session_in_room(room, identifier)
    if player:
        return player

    # 플레이어 번호로 찾기 시도
    try:
        player_number = int(identifier)
        return find_player_by_number(room, player_number)
    except ValueError:
        return None


def get_connected_players(room: Room) -> List[Player]:
    """연결된 플레이어 목록 조회

    Args:
        room: 검색할 방

    Returns:
        연결된 플레이어 리스트
    """
    if not room:
        return []

    return [player for player in room.players if player.is_connected]


def get_disconnected_players(room: Room) -> List[Player]:
    """연결이 끊긴 플레이어 목록 조회

    Args:
        room: 검색할 방

    Returns:
        연결이 끊긴 플레이어 리스트
    """
    if not room:
        return []

    return [player for player in room.players if not player.is_connected]


def is_all_players_connected(room: Room) -> bool:
    """모든 플레이어가 연결되어 있는지 확인

    Args:
        room: 확인할 방

    Returns:
        모든 플레이어가 연결되어 있으면 True
    """
    if not room or not room.players:
        return False

    return all(player.is_connected for player in room.players)


def is_any_player_connected(room: Room) -> bool:
    """한 명이라도 연결된 플레이어가 있는지 확인

    Args:
        room: 확인할 방

    Returns:
        연결된 플레이어가 있으면 True
    """
    if not room or not room.players:
        return False

    return any(player.is_connected for player in room.players)
