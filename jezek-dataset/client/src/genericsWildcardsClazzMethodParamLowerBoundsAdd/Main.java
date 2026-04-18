package genericsWildcardsClazzMethodParamLowerBoundsAdd;

import java.util.ArrayList;

import testing_lib.genericsWildcardsClazzMethodParamLowerBoundsAdd.GenericsWildcardsClazzMethodParamLowerBoundsAdd;

public class Main extends GenericsWildcardsClazzMethodParamLowerBoundsAdd {
	
	public static void main(String[] args) {
		GenericsWildcardsClazzMethodParamLowerBoundsAdd constr = new GenericsWildcardsClazzMethodParamLowerBoundsAdd();
		ArrayList<String> param1 = new ArrayList<String>();
		constr.method1(param1);
	}

	@Override
	public void method1(ArrayList<?> param1) {

	}
}
