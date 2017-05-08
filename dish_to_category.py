def generate_features_and_labels():
    import load_categories
    categories = load_categories.categories
    categories.sort()
    import load_dishes
    dishes = load_dishes.dishes
    dishes.sort()
    
    if not 'recipes' in globals():
        import load_all_recipes
        recipes = load_all_recipes.load_all_recipes()
        
    all_categories = []
    for category_list in recipes['categories']:
        for category in category_list:
            all_categories.append(category)
            
    for index, category in enumerate(all_categories):
        all_categories[index] = category.replace(" ","_")
     
    from sklearn.feature_extraction.text import CountVectorizer
    count_vect = CountVectorizer()
    #variables named with 'td' are a term-doc matrix
    recipes_td = count_vect.fit_transform(all_categories)
    categories_td = count_vect.transform(categories)
    dishes_td = count_vect.transform(dishes)
    num_categories = np.shape(recipes_td)[1]
    
    val, categories_ind = np.where(categories_td.sum(axis=0) == 1)
    val, dishes_ind = np.where(dishes_td.sum(axis=0) == 1)
        
    X = []
    Y = []
    recipes_used = []
    print("encoding features and lablels...")
    for index, category_list in enumerate(recipes['categories']):
        td = count_vect.transform(category_list)
        dishes_in_recipe = np.intersect1d(td.indices, dishes_ind)
        if dishes_in_recipe.size == 0:
            continue
        categories_in_recipe = np.intersect1d(td.indices, categories_ind)
        if categories_in_recipe.size == 0:
            continue
        X.append(dishes_in_recipe)
        Y.append(categories_in_recipe)
        recipes_used.append(
                {'raw_text':recipes['raw_text'][index],
                 'categories':recipes['categories'][index], 
                 'ingredients':recipes['ingredients'][index]})
    #    print(recipes['raw_text'][index])
    from sklearn.preprocessing import MultiLabelBinarizer
    feature_mlb = MultiLabelBinarizer().fit(X)
    label_mlb = MultiLabelBinarizer().fit(Y)
    X_t = feature_mlb.transform(X)
    Y_t = label_mlb.transform(Y)
    
    missing_dishes_ind = np.setdiff1d(dishes_ind,feature_mlb.classes_)    
    num_missing_dishes = np.shape(missing_dishes_ind)[0]
    missing_dishes_td = sp.sparse.csr_matrix((num_missing_dishes,num_categories))
    for i in range(num_missing_dishes):
        j = missing_dishes_ind[i]
        missing_dishes_td[i,j] = 1
    missing_dishes = count_vect.inverse_transform(missing_dishes_td)
    
    missing_categories_ind = np.setdiff1d(categories_ind, label_mlb.classes_)
    num_missing_categories = np.shape(missing_categories_ind)[0]
    missing_categories_td = sp.sparse.csr_matrix((num_missing_categories,num_categories))
    for i in range(num_missing_categories):
        j = missing_categories_ind[i]
        missing_categories_td[i,j] = 1
    missing_categories = count_vect.inverse_transform(missing_categories_td)
    
    dishes_ind = np.setdiff1d(dishes_ind, missing_dishes_ind)
    categories_ind = np.setdiff1d(categories_ind, missing_categories_ind)
    
    print("ignoring:\n",missing_dishes,missing_categories)
    
    p = dishes_ind.size
    q = categories_ind.size
    
    feature_mapping = sp.sparse.csr_matrix((p,num_categories))
    for i in range(p):
        j = dishes_ind[i]
        feature_mapping[i,j] = 1
    label_mapping = sp.sparse.csr_matrix((q,num_categories))
    for i in range(q):
        j = categories_ind[i]
        label_mapping[i,j] = 1
                     
    dishes_str = count_vect.inverse_transform(feature_mapping)
    categories_str = count_vect.inverse_transform(label_mapping)
    return X_t, Y_t, dishes_str, categories_str, recipes_used

def train_multi_label_classifier(X,Y):
    n,q = np.shape(Y)
    models = []
#    for label in tqdm(range(1)):
    for label in tqdm(range(q)):
        y = Y[:,label]
        model = train_single_label_classifier(X,y)
        models.append(model)
    return models

def train_single_label_classifier(X,y):
    dtrain = xgb.DMatrix(X,label=y)
    param = {'objective':'binary:logistic','nthread':4,
             'nfold':10,'max_depth':8}
    xgb.cv(params = param, dtrain = dtrain, metrics={'error@0.1'}, seed = 0,
       callbacks=[xgb.callback.print_evaluation(show_stdv=True)])
    model = xgb.train(params = param, dtrain = dtrain)
#    model = xgb.XGBClassifier(max_depth = 8, nthread = 4).fit(X, y)
    return model
    
    
if __name__ == "__main__":
    import numpy as np
    import scipy as sp
    import matplotlib.pyplot as plt
    import xgboost as xgb
    from tqdm import tqdm
    
    if not 'X' in globals():
        X, Y, dishes_str, categories_str, recipes_used\
        = generate_features_and_labels()
    print("done encoding features and labels")
    
    print("example of data format:\n")
    print(">>recipes_used[0]['raw_text']")
    print(recipes_used[0]['raw_text'])
    print(">>dishes_str[np.where(X[0,:])[0][0]]")
    print(dishes_str[np.where(X[0,:])[0][0]])
    print(">>categories_str[np.where(Y[0,:])[0][0]]")
    print(categories_str[np.where(Y[0,:])[0][0]])
        
    n, p = np.shape(X)
    n, q = np.shape(Y)
    split = int(np.round(0.05*n))
    X_test = X[:split,:]
    Y_test = Y[:split,:]
    X_train = X[split:,:]
    Y_train = X[split:,:]
    
    models = train_multi_label_classifier(X_train,Y_train)
    
    
    