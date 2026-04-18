package genericsWildcardsClazzMethodParamAdd;

import java.util.ArrayList;

import testing_lib.genericsWildcardsClazzMethodParamAdd.GenericsWildcardsClazzMethodParamAdd;

public class Main extends GenericsWildcardsClazzMethodParamAdd {

	public static void main(String[] args) {
		GenericsWildcardsClazzMethodParamAdd constr = new GenericsWildcardsClazzMethodParamAdd();
		ArrayList<String> param1 = new ArrayList<String>();
		constr.method1(param1);
	}

	@Override
	public void method1(ArrayList<String> param1) {

	}
	
}
