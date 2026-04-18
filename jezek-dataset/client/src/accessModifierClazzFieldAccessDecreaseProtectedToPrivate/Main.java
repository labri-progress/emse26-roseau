package accessModifierClazzFieldAccessDecreaseProtectedToPrivate;

import testing_lib.accessModifierClazzFieldAccessDecreaseProtectedToPrivate.AccessModifierClazzFieldAccessDecreaseProtectedToPrivate;

public class Main extends AccessModifierClazzFieldAccessDecreaseProtectedToPrivate {

	public static void main(String[] args) {
		
		Main constr = new Main();
		
		Integer test = constr.field;
	}
	
}

