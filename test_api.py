import urllib.request
import urllib.parse
import json

BASE_URL = 'http://127.0.0.1:5000'

def http_request(url, method='GET', data=None, headers=None):
    if headers is None:
        headers = {}
    if data and isinstance(data, dict):
        data = json.dumps(data).encode('utf-8')
        headers['Content-Type'] = 'application/json'

    req = urllib.request.Request(BASE_URL + url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode('utf-8')
            return response.status, json.loads(res_body) if res_body else {}, response.headers
    except urllib.error.HTTPError as e:
        res_body = e.read().decode('utf-8')
        return e.code, json.loads(res_body) if res_body else {}, e.headers

def run_tests():
    print("==================================================")
    print("   RUNNING AUTOMATED SCRS FULL FEATURE TESTS")
    print("==================================================")

    # 1. Health Check
    status, body, _ = http_request('/health')
    assert status == 200
    print("[PASS] Health Check Passed:", body.get('system'))

    # 2. Login as Admin
    status, body, headers = http_request('/api/auth/login', method='POST', data={
        'email': 'admin@university.edu',
        'password': 'admin123'
    })
    assert status == 200
    cookie = headers.get('Set-Cookie')
    auth_headers = {'Cookie': cookie} if cookie else {}
    print("[PASS] Admin Login Passed:", body['user']['name'])

    # 3. Test Manage Users CRUD via /api/users
    # a. List Users
    status, users, _ = http_request('/api/users', headers=auth_headers)
    assert status == 200
    initial_user_count = len(users)
    print(f"[PASS] List Users API Passed. Initial Count: {initial_user_count}")

    # b. Create New User
    status, new_user_res, _ = http_request('/api/users', method='POST', headers=auth_headers, data={
        'name': 'Test Faculty Member',
        'email': 'test.faculty@university.edu',
        'password': 'testpassword123',
        'role': 'Faculty',
        'department_id': 1
    })
    assert status == 201
    created_user_id = new_user_res['user_id']
    print(f"[PASS] Create User Passed. New User ID: {created_user_id}")

    # c. Validate Duplicate Email
    status, dup_res, _ = http_request('/api/users', method='POST', headers=auth_headers, data={
        'name': 'Duplicate Member',
        'email': 'test.faculty@university.edu',
        'password': 'testpassword123',
        'role': 'Faculty',
        'department_id': 1
    })
    assert status == 400
    assert 'already' in dup_res.get('error', '').lower()
    print("[PASS] Duplicate Email Validation Passed:", dup_res.get('error'))

    # d. Get User Detail
    status, user_detail, _ = http_request(f'/api/users/{created_user_id}', headers=auth_headers)
    assert status == 200
    assert user_detail['name'] == 'Test Faculty Member'
    print("[PASS] Get User Detail Passed:", user_detail['email'])

    # e. Update User
    status, update_res, _ = http_request(f'/api/users/{created_user_id}', method='PUT', headers=auth_headers, data={
        'name': 'Test Faculty Member Updated',
        'email': 'test.faculty@university.edu',
        'role': 'Faculty',
        'department_id': 2
    })
    assert status == 200
    print("[PASS] Update User Passed!")

    # f. Delete User
    status, del_res, _ = http_request(f'/api/users/{created_user_id}', method='DELETE', headers=auth_headers)
    assert status == 200
    print("[PASS] Delete User Passed!")

    # 4. Test Notification System
    status, notif_data, _ = http_request('/api/notifications', headers=auth_headers)
    assert status == 200
    print(f"[PASS] Notifications API Passed. Initial Unread count: {notif_data.get('unread_count')}")

    notifications = notif_data.get('notifications', [])
    if notifications:
        target_notif = notifications[0]
        status, single_read_res, _ = http_request(f"/api/notifications/{target_notif['notification_id']}/read", method='PUT', headers=auth_headers)
        assert status == 200
        print(f"[PASS] Single Notification Mark-Read Passed for Notif #{target_notif['notification_id']}")

    status, read_res, _ = http_request('/api/notifications/read-all', method='PUT', headers=auth_headers)
    assert status == 200
    print("[PASS] Mark All Notifications Read Passed!")

    # Re-verify unread count is now 0
    status, notif_data_after, _ = http_request('/api/notifications', headers=auth_headers)
    assert notif_data_after.get('unread_count') == 0
    print("[PASS] Verified Unread Notifications Count is 0 after mark-read!")

    print("\n==================================================")
    print("   ALL MANAGE USERS & NOTIFICATION TESTS PASSED!  ")
    print("==================================================")

if __name__ == '__main__':
    run_tests()
