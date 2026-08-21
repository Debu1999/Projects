from auth import save_cache_to_db, load_cache_from_db
 
TEST_USER_ID = 2
 
test_data = "this-is-a-test-msal-cache"
 
save_cache_to_db(TEST_USER_ID, test_data)
 
loaded_data = load_cache_from_db(TEST_USER_ID)
 
print("Loaded data:", loaded_data)
 
if loaded_data == test_data:
    print("Token cache database test successful!")
else:
    print("Token cache database test FAILED!")